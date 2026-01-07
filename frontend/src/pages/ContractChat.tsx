import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, FileText, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { api, API_BASE } from '../services/api';
import './ContractChat.css';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
    timestamp: Date;
}

interface Source {
    contract_id: string;
    title: string;
    excerpt: string;
    relevance_score: number;
}

const ContractChat: React.FC = () => {
    const [workspaces, setWorkspaces] = useState<any[]>([]);
    const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // ワークスペース読み込み
    useEffect(() => {
        const loadWorkspaces = async () => {
            setError(null);
            try {
                const data = await api.getWorkspaces();
                setWorkspaces(data);
                if (data && data.length > 0) {
                    setSelectedWorkspaceId(data[0].id);
                } else {
                    setError('ワークスペースが見つかりません。契約書をアップロードするワークスペースが必要です。');
                }
            } catch (err: any) {
                console.error('Failed to load workspaces:', err);
                if (err.message.includes('401') || err.message.includes('無効なトークン')) {
                    setError('セッションが期限切れです。一度ログアウトして再度ログインしてください。');
                } else {
                    setError('ワークスペースの読み込みに失敗しました。サーバーの状態を確認してください。');
                }
            }
        };
        loadWorkspaces();
    }, []);

    // 自動スクロール
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || !selectedWorkspaceId || loading) return;

        const userMessage: Message = {
            role: 'user',
            content: input,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_BASE}/rag/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    query: userMessage.content,
                    workspace_id: selectedWorkspaceId,
                    limit: 5
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('セッションが期限切れです。再ログインしてください。');
                }
                throw new Error('AIの回答生成中にエラーが発生しました');
            }

            const data = await response.json();

            const assistantMessage: Message = {
                role: 'assistant',
                content: data.answer,
                sources: data.sources,
                timestamp: new Date()
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (err: any) {
            setError(err.message || 'エラーが発生しました');

            // エラーメッセージをチャットに表示
            const errorMessage: Message = {
                role: 'assistant',
                content: `申し訳ございません。エラーが発生しました: ${err.message}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="contract-chat-page">
            <div className="chat-container">
                <header className="chat-header">
                    <div className="header-content">
                        <h1><MessageSquare size={24} /> 契約アシスタント</h1>
                        <p>契約書の内容について質問してください。AIが回答します。</p>
                    </div>
                    <select
                        value={selectedWorkspaceId}
                        onChange={(e) => setSelectedWorkspaceId(e.target.value)}
                        className="workspace-select"
                        disabled={workspaces.length === 0}
                    >
                        {workspaces.length === 0 ? (
                            <option value="">（ワークスペースなし）</option>
                        ) : (
                            workspaces.map(ws => (
                                <option key={ws.id} value={ws.id}>{ws.name}</option>
                            ))
                        )}
                    </select>
                </header>

                <div className="messages-container">
                    {messages.length === 0 ? (
                        <div className="empty-state">
                            <MessageSquare size={48} />
                            <h3>質問してみましょう</h3>
                            <p>例: 損害賠償の上限は？ / 秘密保持義務の期間は？</p>
                        </div>
                    ) : (
                        messages.map((msg, idx) => (
                            <MessageBubble key={idx} message={msg} />
                        ))
                    )}
                    {loading && (
                        <div className="message assistant">
                            <div className="message-content">
                                <Loader2 className="animate-spin" size={20} />
                                <span>回答を生成中...</span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form onSubmit={handleSend} className="chat-input-form">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="契約書について質問してください..."
                        className="chat-input"
                        disabled={loading || !selectedWorkspaceId}
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim() || !selectedWorkspaceId}
                        className="send-button"
                    >
                        <Send size={20} />
                    </button>
                </form>
            </div>
        </div>
    );
};

const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
    const [showSources, setShowSources] = useState(false);

    if (message.role === 'user') {
        return (
            <div className="message user">
                <div className="message-content">{message.content}</div>
            </div>
        );
    }

    return (
        <div className="message assistant">
            <div className="message-content">
                <div className="answer-text">{message.content}</div>

                {message.sources && message.sources.length > 0 && (
                    <div className="sources-section">
                        <button
                            className="sources-toggle"
                            onClick={() => setShowSources(!showSources)}
                        >
                            <FileText size={16} />
                            <span>出典 ({message.sources.length}件)</span>
                            {showSources ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>

                        {showSources && (
                            <div className="sources-list">
                                {message.sources.map((source, idx) => (
                                    <div key={idx} className="source-item">
                                        <div className="source-header">
                                            <span className="source-title">{source.title}</span>
                                            <span className="relevance-badge">
                                                関連度: {(source.relevance_score * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <div className="source-excerpt">{source.excerpt}</div>
                                        <a
                                            href={`/contracts/${source.contract_id}`}
                                            className="source-link"
                                        >
                                            契約書を表示 →
                                        </a>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ContractChat;
