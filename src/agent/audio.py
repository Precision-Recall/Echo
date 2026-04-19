import pyaudio
import asyncio
import queue
import threading

class AudioManager:
    """
    Manages audio input (microphone) and output (speaker) streams.
    Format: 16kHz, 16-bit PCM, Mono (Gemini standard).
    
    Based on working pattern with improved output buffering.
    """
    
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    INPUT_RATE = 16000   # Mic input: 16kHz
    OUTPUT_RATE = 24000  # Gemini output: 24kHz
    CHUNK = 512          # Smaller chunk for better responsiveness
    
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.input_queue = asyncio.Queue()
        self.output_queue = queue.Queue()
        self._is_playing = False
        
        # Bug 2: Use threading.Event for cross-thread _is_recording flag
        self._recording_event = threading.Event()
        
        # Bug 2: Use threading.Lock for cross-thread _writing_active flag
        self._write_lock = threading.Lock()
        self._writing_active = False
        
        # Bug 3: Protect output_stream reference against TOCTOU races
        self._stream_lock = threading.Lock()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def start_recording(self):
        """Start capturing microphone input using callback (working pattern)"""
        if self._recording_event.is_set():
            return

        # Bug 2: Set event instead of boolean
        self._recording_event.set()
        # Bug 10: Use get_running_loop() instead of deprecated get_event_loop()
        loop = asyncio.get_running_loop()
        
        def callback(in_data, frame_count, time_info, status):
            # Bug 2: Thread-safe check via Event.is_set()
            if self._recording_event.is_set():
                # Half-Duplex: Drop input if we are currently speaking (writing to output)
                # or if there is pending audio in the output queue.
                # Bug 2: Thread-safe read of _writing_active via lock
                with self._write_lock:
                    is_writing = self._writing_active
                is_speaking = is_writing or not self.output_queue.empty()
                
                if not is_speaking:
                    loop.call_soon_threadsafe(self.input_queue.put_nowait, in_data)
            return (None, pyaudio.paContinue)

        self.input_stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.INPUT_RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            stream_callback=callback
        )
        self.input_stream.start_stream()
        print(f"Recording started: {self.INPUT_RATE}Hz, chunk={self.CHUNK}")

    async def stop_recording(self):
        """Stop capturing microphone input"""
        # Bug 2: Clear event instead of boolean
        self._recording_event.clear()
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
    
    def pause_recording(self):
        """Pause recording without closing stream (faster resume)"""
        # Bug 2: Clear event instead of boolean
        self._recording_event.clear()
        # Clear any pending audio
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except:
                break
    
    def resume_recording(self):
        """Resume recording after pause"""
        # Bug 2: Set event instead of boolean
        self._recording_event.set()

    async def get_audio_chunk(self):
        """Get next chunk of audio data from mic"""
        return await self.input_queue.get()

    def start_playback(self):
        """Start playing audio using blocking write (official pattern)"""
        if self._is_playing:
            return
            
        self._is_playing = True
        
        # Open output stream without callback (blocking mode)
        # Bug 3: Protect stream creation under lock
        with self._stream_lock:
            self.output_stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.OUTPUT_RATE,
                output=True,
            )
        
        # Start playback thread
        self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._playback_thread.start()
    
    def _playback_loop(self):
        """Background thread for blocking audio write (matches official example)"""
        while self._is_playing:
            try:
                # Block waiting for audio data
                data = self.output_queue.get(timeout=0.5)
                # Bug 3: Hold stream lock while checking and writing to output_stream
                with self._stream_lock:
                    if data and self.output_stream:
                        # Bug 2: Thread-safe write of _writing_active via lock
                        with self._write_lock:
                            self._writing_active = True
                        try:
                            self.output_stream.write(data)
                        finally:
                            with self._write_lock:
                                self._writing_active = False
            except queue.Empty:
                continue  # No data, keep waiting
            except Exception as e:
                if self._is_playing:
                    print(f"Playback error: {e}")
                break

    def stop_playback(self):
        """Stop audio playback"""
        self._is_playing = False
        # Bug 3: Hold stream lock while closing output_stream
        with self._stream_lock:
            if self.output_stream:
                try:
                    self.output_stream.stop_stream()
                    self.output_stream.close()
                except:
                    pass
                self.output_stream = None
        # Clear queue
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except:
                break

    def play_audio_chunk(self, data: bytes):
        """Add audio chunk to playback queue"""
        if not data:
            return
        if not self._is_playing:
            self.start_playback()
        try:
            self.output_queue.put_nowait(data)
        except queue.Full:
            pass  # Drop if queue full to prevent lag

    def close(self):
        """Cleanup resources"""
        print("Closing audio manager...")
        self.stop_playback()
        if self.input_stream:
            try:
                self.input_stream.close()
            except:
                pass
        self.p.terminate()
        print("Audio manager closed")