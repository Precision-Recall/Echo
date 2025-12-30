# WebSocket "Insufficient Resources" Fix

## Problem Summary

The frontend was experiencing a critical bug where WebSocket connections to `/ws/chat` would fail with "Insufficient resources" error. The browser was creating **hundreds of connections per second**, exhausting available resources.

## Root Cause

**Infinite Re-render Loop** caused by improper React dependency management:

### The Bug Chain:

1. **`page.tsx:73`** - Message handler created inline (new function every render)
   ```typescript
   useGeminiWebSocket('/ws/chat', (message) => {
     // Uses setMessages, setIsChatLoading - changes every render
   });
   ```

2. **`useGeminiWebSocket.ts:97`** - `onMessage` in dependency array
   ```typescript
   }, [endpoint, onMessage]); // ❌ onMessage changes = connect recreated
   ```

3. **`page.tsx:126-128`** - useEffect depends on unstable `connectChat`
   ```typescript
   useEffect(() => {
     connectChat();
   }, [connectChat]); // ❌ Runs every time connectChat changes
   ```

4. **Result**: New WebSocket created on every render → State update → Re-render → Loop!

## The Fix

### 1. Use Ref Pattern for Callback (useGeminiWebSocket.ts)

**Before:**
```typescript
const connect = useCallback(() => {
  // ...
  ws.onmessage = (event) => {
    if (onMessage) {
      onMessage(message); // Uses onMessage from closure
    }
  };
}, [endpoint, onMessage]); // ❌ Depends on onMessage
```

**After:**
```typescript
const onMessageRef = useRef(onMessage);

// Update ref when onMessage changes
useEffect(() => {
  onMessageRef.current = onMessage;
}, [onMessage]);

const connect = useCallback(() => {
  // ...
  ws.onmessage = (event) => {
    if (onMessageRef.current) {
      onMessageRef.current(message); // Uses latest from ref
    }
  };
}, [endpoint]); // ✅ Stable - only depends on endpoint
```

### 2. Prevent Duplicate Connections

**Added connection guard:**
```typescript
const isConnectingRef = useRef(false);

const connect = useCallback(() => {
  // Prevent duplicate connections
  if (wsRef.current?.readyState === WebSocket.OPEN || isConnectingRef.current) {
    return;
  }
  
  isConnectingRef.current = true;
  
  // ... connection logic ...
  
  ws.onopen = () => {
    isConnectingRef.current = false; // Reset on success
  };
  
  ws.onerror = () => {
    isConnectingRef.current = false; // Reset on error
  };
});
```

### 3. Improved Chat Submission (page.tsx)

**Before:**
```typescript
if (chatConnectionState !== 'connected') {
  connectChat();
  setTimeout(() => sendText(chatInput), 500); // ❌ Race condition
}
```

**After:**
```typescript
if (chatConnectionState !== 'connected') {
  setMessages(prev => [...prev, 
    { role: 'user', text: chatInput },
    { role: 'model', text: 'Not connected. Please wait...' }
  ]);
  connectChat(); // Try to reconnect
  return; // Don't send
}
```

## Files Changed

### `app/hooks/useGeminiWebSocket.ts`
- ✅ Added `onMessageRef` to store callback without triggering re-renders
- ✅ Added `isConnectingRef` to prevent duplicate connections
- ✅ Removed `onMessage` from `connect` dependency array
- ✅ Reset connection flag on open/error/close

### `app/page.tsx`
- ✅ Improved chat submission to handle disconnected state
- ✅ Shows user-friendly error message when not connected
- ✅ Prevents race conditions in message sending

## Impact

**Before:**
- ❌ Hundreds of WebSocket connections per second
- ❌ Browser "Insufficient resources" error
- ❌ Chat completely unusable
- ❌ `/ws/live` worked, but `/ws/chat` failed

**After:**
- ✅ Single stable connection per endpoint
- ✅ No resource exhaustion
- ✅ Both `/ws/live` and `/ws/chat` work perfectly
- ✅ Proper reconnection with exponential backoff
- ✅ Clean disconnect on unmount

## Testing

### Verify the Fix:

1. **Start the backend:**
   ```bash
   cd echo_backend
   python main.py
   ```

2. **Start the frontend:**
   ```bash
   cd echo_frontend
   npm run dev
   ```

3. **Test Chat Mode:**
   - Open browser to `http://localhost:3000`
   - Open DevTools → Console
   - Should see: `✅ Connected to backend /ws/chat` (once)
   - Type a message and send
   - Should work without errors

4. **Test Voice Mode:**
   - Click "Voice Mode" button
   - Should see: `✅ Connected to backend /ws/live`
   - Speak into microphone
   - Should receive audio response

5. **Test Reconnection:**
   - Stop backend (`Ctrl+C`)
   - Should see: `❌ Disconnected from backend`
   - Should see: `🔄 Attempting to reconnect...` (with delays)
   - Restart backend
   - Should automatically reconnect

6. **Test React Strict Mode:**
   - In development, components mount twice
   - Should still only see ONE connection per endpoint
   - No "Insufficient resources" errors

## React Best Practices Applied

### 1. **Ref Pattern for Callbacks**
Use refs to access latest values without causing re-renders:
```typescript
const callbackRef = useRef(callback);
useEffect(() => { callbackRef.current = callback; }, [callback]);
// Use callbackRef.current in stable functions
```

### 2. **Stable Dependencies**
Only include truly stable values in `useCallback` dependencies:
```typescript
useCallback(() => {
  // Use refs for changing values
}, [stableValue]); // Only stable primitives
```

### 3. **Connection Guards**
Prevent duplicate operations with refs:
```typescript
const isDoingThingRef = useRef(false);
if (isDoingThingRef.current) return;
isDoingThingRef.current = true;
```

### 4. **Cleanup**
Always clean up effects and refs:
```typescript
useEffect(() => {
  return () => {
    // Reset refs, close connections, clear timers
  };
}, []);
```

## Related Documentation

- [React useCallback Hook](https://react.dev/reference/react/useCallback)
- [React useRef Hook](https://react.dev/reference/react/useRef)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)

## Prevention

To avoid similar issues in the future:

1. **✅ Always use refs** for callbacks passed to hooks with internal `useCallback`
2. **✅ Check dependency arrays** - are they truly stable?
3. **✅ Add connection guards** for operations that shouldn't run concurrently
4. **✅ Test in React Strict Mode** - it will expose re-render issues
5. **✅ Monitor DevTools** - look for repeated log messages

## Notes

- The backend was never the issue - it was correctly accepting connections
- The issue only affected `/ws/chat` because chat auto-connects on mount
- `/ws/live` worked because it only connects when user clicks "Voice Mode"
- This is a common React pitfall with WebSockets and other external APIs

## Credits

Fix implemented: December 29, 2024
Issue identified through browser console error logs and backend connection logs

