import { useState } from 'react';
import { AlertTriangle, Play, FileText, Hash, Clock, Database, Download, Trash2, Eye, CheckCircle } from 'lucide-react';
import { Button } from '../../../ui/Button';
import { Badge } from '../../../ui/Badge';
import { Panel } from '../../../ui/Panel';
import { cn } from '../../../ui/utils';

interface Incident {
    id: string;
    name: string;
    recordedAt: string;
    durationSeconds: number;
    tickCount: number;
    hash: string;
    status: 'recording' | 'completed' | 'verified';
    symbols: string[];
}

const mockIncidents: Incident[] = [
    {
        id: 'bundle_001',
        name: 'AAPL_2026-01-12_morning',
        recordedAt: '2026-01-12T09:30:00Z',
        durationSeconds: 7200,
        tickCount: 45000,
        hash: 'sha256:abc123def456...',
        status: 'verified',
        symbols: ['AAPL'],
    },
    {
        id: 'bundle_002',
        name: 'MSFT_TSLA_2026-01-11',
        recordedAt: '2026-01-11T09:30:00Z',
        durationSeconds: 23400,
        tickCount: 125000,
        hash: 'sha256:789xyz...',
        status: 'completed',
        symbols: ['MSFT', 'TSLA'],
    },
];

export function IncidentsView() {
    const [incidents, setIncidents] = useState<Incident[]>(mockIncidents);
    const [isRecording, setIsRecording] = useState(false);
    const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

    const formatDuration = (seconds: number) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    };

    const handleStartRecording = () => {
        setIsRecording(true);
        // In real implementation: POST /api/v1/incidents/record
    };

    const handleStopRecording = () => {
        setIsRecording(false);
        // In real implementation: POST /api/v1/incidents/{id}/stop
        const newIncident: Incident = {
            id: `bundle_${Date.now()}`,
            name: `Recording_${new Date().toISOString().slice(0, 10)}`,
            recordedAt: new Date().toISOString(),
            durationSeconds: 0,
            tickCount: 0,
            hash: 'pending...',
            status: 'completed',
            symbols: ['AAPL'],
        };
        setIncidents(prev => [newIncident, ...prev]);
    };

    const handleReplay = (incident: Incident) => {
        // Navigate to replay view with this bundle
        console.log('Replay bundle:', incident.id);
    };

    const handleDelete = (id: string) => {
        setIncidents(prev => prev.filter(i => i.id !== id));
    };

    const handleDownload = (incident: Incident) => {
        // Download bundle file
        console.log('Download bundle:', incident.id);
    };

    return (
        <div className="h-full overflow-auto bg-background p-6">
            <div className="max-w-6xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="text-brand" size={28} />
                        <div>
                            <h1 className="text-2xl font-bold text-text">Incidents & Bundles</h1>
                            <p className="text-sm text-text-secondary">Record live sessions for deterministic replay and testing</p>
                        </div>
                    </div>
                    <Button
                        variant={isRecording ? 'danger' : 'primary'}
                        onClick={isRecording ? handleStopRecording : handleStartRecording}
                        className="gap-2"
                    >
                        {isRecording ? (
                            <>
                                <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                                Stop Recording
                            </>
                        ) : (
                            <>
                                <Database size={16} />
                                Start Recording
                            </>
                        )}
                    </Button>
                </div>

                {/* Recording Status */}
                {isRecording && (
                    <Panel className="bg-red-500/10 border-red-500/50 p-4">
                        <div className="flex items-center gap-3">
                            <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
                            <div>
                                <p className="font-semibold text-red-400">Recording in progress...</p>
                                <p className="text-sm text-red-300/70">Capturing live market data for replay bundle</p>
                            </div>
                            <div className="ml-auto text-sm text-red-300 font-mono">
                                00:05:32
                            </div>
                        </div>
                    </Panel>
                )}

                {/* Bundles List */}
                <Panel className="overflow-hidden">
                    <div className="p-4 border-b border-border">
                        <h3 className="font-semibold">Recorded Bundles</h3>
                    </div>
                    <div className="divide-y divide-border">
                        {incidents.length === 0 ? (
                            <div className="p-8 text-center text-text-secondary">
                                <Database size={32} className="mx-auto mb-2 opacity-50" />
                                <p>No recorded bundles</p>
                                <p className="text-sm">Start recording to capture live market data</p>
                            </div>
                        ) : (
                            incidents.map(incident => (
                                <div
                                    key={incident.id}
                                    className={cn(
                                        "p-4 hover:bg-element-bg/50 transition-colors cursor-pointer",
                                        selectedIncident?.id === incident.id && "bg-element-bg"
                                    )}
                                    onClick={() => setSelectedIncident(incident)}
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded bg-element-bg flex items-center justify-center">
                                            <FileText size={20} className="text-text-secondary" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium text-text truncate">{incident.name}</span>
                                                <Badge variant={
                                                    incident.status === 'verified' ? 'success' :
                                                    incident.status === 'recording' ? 'error' : 'default'
                                                }>
                                                    {incident.status === 'verified' && <CheckCircle size={12} className="mr-1" />}
                                                    {incident.status}
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-4 mt-1 text-sm text-text-secondary">
                                                <span className="flex items-center gap-1">
                                                    <Clock size={12} />
                                                    {formatDuration(incident.durationSeconds)}
                                                </span>
                                                <span>{incident.tickCount.toLocaleString()} ticks</span>
                                                <span className="flex items-center gap-1">
                                                    <Hash size={12} />
                                                    {incident.hash.slice(0, 16)}...
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {incident.symbols.map(s => (
                                                <Badge key={s} variant="outline">{s}</Badge>
                                            ))}
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={(e) => { e.stopPropagation(); handleReplay(incident); }}
                                                title="Replay"
                                            >
                                                <Play size={16} />
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={(e) => { e.stopPropagation(); handleDownload(incident); }}
                                                title="Download"
                                            >
                                                <Download size={16} />
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={(e) => { e.stopPropagation(); handleDelete(incident.id); }}
                                                title="Delete"
                                                className="text-red-400 hover:text-red-300"
                                            >
                                                <Trash2 size={16} />
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </Panel>

                {/* Selected Bundle Details */}
                {selectedIncident && (
                    <Panel className="p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Eye size={18} />
                            Bundle Details: {selectedIncident.name}
                        </h3>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span className="text-text-secondary">ID:</span>
                                <span className="ml-2 font-mono">{selectedIncident.id}</span>
                            </div>
                            <div>
                                <span className="text-text-secondary">Recorded:</span>
                                <span className="ml-2">{new Date(selectedIncident.recordedAt).toLocaleString()}</span>
                            </div>
                            <div>
                                <span className="text-text-secondary">Duration:</span>
                                <span className="ml-2">{formatDuration(selectedIncident.durationSeconds)}</span>
                            </div>
                            <div>
                                <span className="text-text-secondary">Tick Count:</span>
                                <span className="ml-2">{selectedIncident.tickCount.toLocaleString()}</span>
                            </div>
                            <div className="col-span-2">
                                <span className="text-text-secondary">Hash:</span>
                                <span className="ml-2 font-mono text-xs break-all">{selectedIncident.hash}</span>
                            </div>
                            <div>
                                <span className="text-text-secondary">Symbols:</span>
                                <span className="ml-2">{selectedIncident.symbols.join(', ')}</span>
                            </div>
                        </div>
                        <div className="mt-4 pt-4 border-t border-border flex gap-2">
                            <Button variant="primary" onClick={() => handleReplay(selectedIncident)}>
                                <Play size={16} className="mr-2" />
                                Load in Replay Mode
                            </Button>
                            <Button variant="secondary" onClick={() => handleDownload(selectedIncident)}>
                                <Download size={16} className="mr-2" />
                                Export Bundle
                            </Button>
                        </div>
                    </Panel>
                )}

                {/* Info Panel */}
                <Panel className="p-4 bg-blue-500/10 border-blue-500/30">
                    <p className="text-sm text-blue-400">
                        <strong>Deterministic Replay:</strong> Bundles capture raw provider events, normalized ticks, bars, and hashes. 
                        Replay mode proves parity via hash verification — ensuring identical bar formation from the same input data.
                    </p>
                </Panel>
            </div>
        </div>
    );
}
