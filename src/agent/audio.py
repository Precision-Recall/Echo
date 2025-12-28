import pyaudio
import asyncio
import queue
import threading

class AudioManager:
    """
    Manages audio input (microphone) and output (speaker) streams.
    Format: 16kHz, 16-bit PCM, Mono (Gemini standard).
    """
    
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    INPUT_RATE = 16000
    OUTPUT_RATE = 24000
    CHUNK = 512
    
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.input_stream = None
        self.output_stream = None
        self.input_queue = asyncio.Queue()
        self.output_queue = queue.Queue()
        self._is_recording = False
        self._is_playing = False
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def start_recording(self):
        """Start capturing microphone input"""
        if self._is_recording:
            return

        self._is_recording = True
        loop = asyncio.get_event_loop()
        
        def callback(in_data, frame_count, time_info, status):
            if self._is_recording:
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

    async def stop_recording(self):
        """Stop capturing microphone input"""
        self._is_recording = False
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None

    async def get_audio_chunk(self):
        """Get next chunk of audio data from mic"""
        return await self.input_queue.get()

    def start_playback(self):
        """Start playing audio from the queue"""
        if self._is_playing:
            return
            
        self._is_playing = True
        
        def callback(in_data, frame_count, time_info, status):
            try:
                data = self.output_queue.get_nowait()
                return (data, pyaudio.paContinue)
            except queue.Empty:
                return (b'\x00' * frame_count * 2, pyaudio.paContinue)

        self.output_stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.OUTPUT_RATE,
            output=True,
            stream_callback=callback
        )
        self.output_stream.start_stream()

    def stop_playback(self):
        """Stop audio playback"""
        self._is_playing = False
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None

    def play_audio_chunk(self, data: bytes):
        """Add audio chunk to playback queue"""
        if not self._is_playing:
            self.start_playback()
        self.output_queue.put(data)

    def close(self):
        """Cleanup resources"""
        self.stop_playback()
        # stop_recording is async, so we assume caller handles it or we do best effort
        if self.input_stream:
            self.input_stream.close()
        self.p.terminate()
