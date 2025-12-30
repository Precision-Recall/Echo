// Type declarations for Electron preload API
export { };

declare global {
    interface Window {
        ipcRenderer?: {
            send: (channel: string, data?: any) => void;
            on: (channel: string, func: (event: any, ...args: any[]) => void) => void;
            removeAllListeners: (channel: string) => void;
            invoke: (channel: string, data?: any) => Promise<any>;
        };
    }
}
