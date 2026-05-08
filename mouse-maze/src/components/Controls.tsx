import React from 'react';

interface ControlsProps {
    onGenerate: () => void;
    onStart: () => void;
    isNavigating: boolean;
}

const Controls: React.FC<ControlsProps> = ({ onGenerate, onStart, isNavigating }) => {
    return (
        <div className="controls-panel glassmorphism">
            <button
                className="btn primary"
                onClick={onGenerate}
                disabled={isNavigating}
            >
                生成新迷宮 (Generate Maze)
            </button>
            <button
                className="btn secondary"
                onClick={onStart}
                disabled={isNavigating}
            >
                開始導航 (Start Navigation)
            </button>
        </div>
    );
};

export default Controls;
