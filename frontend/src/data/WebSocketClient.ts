import type { WSMessage } from '../core/types.ts';

type MessageCallback = (msg: WSMessage) => void;

export class WebSocketClient {
    private url: string;
    private socket: WebSocket | null = null;
    private onMessage: MessageCallback;
    private shouldReconnect: boolean = true;
    private reconnectDelay: number = 2000;

    constructor(url: string, onMessage: MessageCallback) {
        this.url = url;
        this.onMessage = onMessage;
    }

    public connect() {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            console.log('WS already connected or connecting');
            return;
        }

        this.shouldReconnect = true;
        console.log(`Connecting to ${this.url}`);

        try {
            this.socket = new WebSocket(this.url);

            this.socket.onopen = () => {
                console.log('WS Connected');
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data) as WSMessage;
                    this.onMessage(data);
                } catch (e) {
                    console.error('Failed to parse WS message', e);
                }
            };

            this.socket.onclose = () => {
                if (this.shouldReconnect) {
                    console.log('WS Closed, recombining...');
                    setTimeout(() => this.connect(), this.reconnectDelay);
                } else {
                    console.log('WS Disconnected Cleanly');
                }
            };

            this.socket.onerror = (e) => {
                console.error('WS Error', e);
                // On error, let onclose handle reconnect if valid
            };
        } catch (e) {
            console.error('WS Connection Creation Failed', e);
            if (this.shouldReconnect) {
                setTimeout(() => this.connect(), this.reconnectDelay);
            }
        }
    }

    public disconnect() {
        this.shouldReconnect = false;
        if (this.socket) {
            this.socket.onclose = null; // Prevent reconnect trigger during manual close
            this.socket.close();
            this.socket = null;
        }
    }
}
