import React, { useRef, useEffect } from 'react';
import './ChainOfThought.css';

interface ThinkingStep {
    id: string;
    type: 'thought' | 'tool' | 'result' | 'error';
    content: string;
    timestamp: number;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    text: string;
    timestamp: number;
}

interface ChainOfThoughtProps {
    steps: ThinkingStep[];
    messages: Message[];
    currentTranscription: string;
}

const ChainOfThought: React.FC<ChainOfThoughtProps> = ({
    steps,
    messages,
    currentTranscription
}) => {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
    }, [steps, messages]);

    const getStepIcon = (type: ThinkingStep['type']) => {
        switch (type) {
            case 'thought': return '💭';
            case 'tool': return '🔧';
            case 'result': return '✅';
            case 'error': return '❌';
            default: return '•';
        }
    };

    const getStepClass = (type: ThinkingStep['type']) => {
        return `cot-step cot-step-${type}`;
    };

    return (
        <div className="chain-of-thought">
            {/* Header */}
            <div className="cot-header">
                <span className="cot-title">Chain of Thought</span>
                <span className="cot-count">{steps.length} steps</span>
            </div>

            {/* Steps List */}
            <div className="cot-list" ref={scrollRef}>
                {steps.length === 0 ? (
                    <div className="cot-empty">
                        <span className="cot-empty-icon">🧠</span>
                        <p>Press <strong>SPACE</strong> to start</p>
                        <p className="cot-empty-sub">Thinking steps will appear here</p>
                    </div>
                ) : (
                    steps.map((step, index) => (
                        <div key={step.id} className={getStepClass(step.type)}>
                            <div className="cot-step-line">
                                {index < steps.length - 1 && <div className="cot-connector" />}
                            </div>
                            <div className="cot-step-icon">{getStepIcon(step.type)}</div>
                            <div className="cot-step-content">
                                <span className="cot-step-text">{step.content}</span>
                                <span className="cot-step-time">
                                    {new Date(step.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                            </div>
                        </div>
                    ))
                )}

                {/* Live transcription indicator */}
                {currentTranscription && (
                    <div className="cot-live">
                        <div className="cot-live-dot" />
                        <span>{currentTranscription}</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChainOfThought;
