import React, { useState, useEffect } from 'react';
import type { Point } from '../utils/goEngine';
import { type AiConfig, validateApiKey } from '../services/aiService';

interface SetupPanelProps {
  onStartGame: (config: {
    boardSize: number;
    rules: 'Chinese' | 'Japanese';
    handicap: number;
    komi: number;
    blackPlayer: { type: 'human' | 'ai'; aiConfig: AiConfig };
    whitePlayer: { type: 'human' | 'ai'; aiConfig: AiConfig };
  }) => void;
}

// Get the coordinates of handicap stones based on board size and count (2 to 9)
export function getHandicapPoints(size: number, count: number): Point[] {
  if (count < 2) return [];

  // Indices for star points
  // 19x19: 3, 9, 15
  // 13x13: 3, 6, 9
  // 9x9: 2, 4, 6
  const low = size === 19 ? 3 : size === 13 ? 3 : 2;
  const mid = size === 19 ? 9 : size === 13 ? 6 : 4;
  const high = size === 19 ? 15 : size === 13 ? 9 : 6;

  const points = {
    topLeft: { x: low, y: low },
    topRight: { x: low, y: high },
    bottomLeft: { x: high, y: low },
    bottomRight: { x: high, y: high },
    center: { x: mid, y: mid },
    leftMid: { x: mid, y: low },
    rightMid: { x: mid, y: high },
    topMid: { x: low, y: mid },
    bottomMid: { x: high, y: mid }
  };

  switch (count) {
    case 2:
      return [points.topRight, points.bottomLeft];
    case 3:
      return [points.topRight, points.bottomLeft, points.bottomRight];
    case 4:
      return [points.topLeft, points.topRight, points.bottomLeft, points.bottomRight];
    case 5:
      return [points.topLeft, points.topRight, points.bottomLeft, points.bottomRight, points.center];
    case 6:
      return [points.topLeft, points.topRight, points.bottomLeft, points.bottomRight, points.leftMid, points.rightMid];
    case 7:
      return [points.topLeft, points.topRight, points.bottomLeft, points.bottomRight, points.leftMid, points.rightMid, points.center];
    case 8:
      return [points.topLeft, points.topRight, points.bottomLeft, points.bottomRight, points.leftMid, points.rightMid, points.topMid, points.bottomMid];
    case 9:
      return [points.topLeft, points.topRight, points.bottomLeft, points.bottomRight, points.leftMid, points.rightMid, points.topMid, points.bottomMid, points.center];
    default:
      return [];
  }
}

export const SetupPanel: React.FC<SetupPanelProps> = ({ onStartGame }) => {
  const [boardSize, setBoardSize] = useState<number>(19);
  const [rules, setRules] = useState<'Chinese' | 'Japanese'>('Chinese');
  const [handicap, setHandicap] = useState<number>(0);
  const [komi, setKomi] = useState<number>(7.5);

  // Black player states
  const [blackType, setBlackType] = useState<'human' | 'ai'>('human');
  const [blackProvider, setBlackProvider] = useState<AiConfig['provider']>('local');
  const [blackModel, setBlackModel] = useState<string>('gemini-2.5-flash');
  const [blackKey, setBlackKey] = useState<string>('');
  const [blackProxyUrl, setBlackProxyUrl] = useState<string>('');

  // White player states
  const [whiteType, setWhiteType] = useState<'human' | 'ai'>('human');
  const [whiteProvider, setWhiteProvider] = useState<AiConfig['provider']>('local');
  const [whiteModel, setWhiteModel] = useState<string>('gemini-2.5-flash');
  const [whiteKey, setWhiteKey] = useState<string>('');
  const [whiteProxyUrl, setWhiteProxyUrl] = useState<string>('');

  // API Key validation states
  const [blackKeyStatus, setBlackKeyStatus] = useState<{ loading: boolean; message: string; success: boolean | null }>({
    loading: false,
    message: '',
    success: null
  });
  const [whiteKeyStatus, setWhiteKeyStatus] = useState<{ loading: boolean; message: string; success: boolean | null }>({
    loading: false,
    message: '',
    success: null
  });

  const handleVerifyKey = async (player: 'B' | 'W') => {
    const provider = player === 'B' ? blackProvider : whiteProvider;
    const apiKey = player === 'B' ? blackKey : whiteKey;
    const proxyUrl = player === 'B' ? blackProxyUrl : whiteProxyUrl;
    const setStatus = player === 'B' ? setBlackKeyStatus : setWhiteKeyStatus;

    if (provider === 'local' || provider === 'mcts') return;

    setStatus({ loading: true, message: '正在驗證金鑰...', success: null });
    try {
      const res = await validateApiKey(provider, apiKey, proxyUrl);
      setStatus({ loading: false, message: res.message, success: res.valid });
    } catch (err: any) {
      setStatus({ loading: false, message: `驗證時發生未知錯誤：${err.message || err}`, success: false });
    }
  };

  // Auto-adjust Komi when size/rules/handicap changes
  useEffect(() => {
    if (handicap > 0) {
      setKomi(0.5); // Tie breaker komi for handicap games
    } else {
      if (rules === 'Chinese') {
        setKomi(7.5);
      } else {
        setKomi(6.5);
      }
    }
  }, [boardSize, rules, handicap]);

  // Load API Keys and Proxies from localStorage on mount
  useEffect(() => {
    const savedGeminiKey = localStorage.getItem('go_api_key_gemini') || '';
    const savedGroqKey = localStorage.getItem('go_api_key_groq') || '';
    const savedOpenRouterKey = localStorage.getItem('go_api_key_openrouter') || '';
    const savedOpenAiKey = localStorage.getItem('go_api_key_openai') || '';
    const savedAnthropicKey = localStorage.getItem('go_api_key_anthropic') || '';

    const savedGeminiProxy = localStorage.getItem('go_proxy_url_gemini') || '';
    const savedGroqProxy = localStorage.getItem('go_proxy_url_groq') || '';
    const savedOpenRouterProxy = localStorage.getItem('go_proxy_url_openrouter') || '';
    const savedOpenAiProxy = localStorage.getItem('go_proxy_url_openai') || '';
    const savedAnthropicProxy = localStorage.getItem('go_proxy_url_anthropic') || '';

    // Apply saved key & proxy for Black
    if (blackProvider === 'gemini') {
      setBlackKey(savedGeminiKey);
      setBlackProxyUrl(savedGeminiProxy);
    } else if (blackProvider === 'groq') {
      setBlackKey(savedGroqKey);
      setBlackProxyUrl(savedGroqProxy);
    } else if (blackProvider === 'openrouter') {
      setBlackKey(savedOpenRouterKey);
      setBlackProxyUrl(savedOpenRouterProxy);
    } else if (blackProvider === 'openai') {
      setBlackKey(savedOpenAiKey);
      setBlackProxyUrl(savedOpenAiProxy);
    } else if (blackProvider === 'anthropic') {
      setBlackKey(savedAnthropicKey);
      setBlackProxyUrl(savedAnthropicProxy);
    } else {
      setBlackKey('');
      setBlackProxyUrl('');
    }

    // Apply saved key & proxy for White
    if (whiteProvider === 'gemini') {
      setWhiteKey(savedGeminiKey);
      setWhiteProxyUrl(savedGeminiProxy);
    } else if (whiteProvider === 'groq') {
      setWhiteKey(savedGroqKey);
      setWhiteProxyUrl(savedGroqProxy);
    } else if (whiteProvider === 'openrouter') {
      setWhiteKey(savedOpenRouterKey);
      setWhiteProxyUrl(savedOpenRouterProxy);
    } else if (whiteProvider === 'openai') {
      setWhiteKey(savedOpenAiKey);
      setWhiteProxyUrl(savedOpenAiProxy);
    } else if (whiteProvider === 'anthropic') {
      setWhiteKey(savedAnthropicKey);
      setWhiteProxyUrl(savedAnthropicProxy);
    } else {
      setWhiteKey('');
      setWhiteProxyUrl('');
    }
  }, [blackProvider, whiteProvider]);

  // Save API Key helper
  const handleKeyChange = (player: 'B' | 'W', val: string) => {
    const provider = player === 'B' ? blackProvider : whiteProvider;
    if (player === 'B') {
      setBlackKey(val);
      setBlackKeyStatus({ loading: false, message: '', success: null });
    } else {
      setWhiteKey(val);
      setWhiteKeyStatus({ loading: false, message: '', success: null });
    }

    if (provider !== 'local' && provider !== 'mcts') {
      localStorage.setItem(`go_api_key_${provider}`, val);
    }
  };

  // Save Proxy URL helper
  const handleProxyUrlChange = (player: 'B' | 'W', val: string) => {
    const provider = player === 'B' ? blackProvider : whiteProvider;
    if (player === 'B') {
      setBlackProxyUrl(val);
    } else {
      setWhiteProxyUrl(val);
    }

    if (provider !== 'local' && provider !== 'mcts') {
      localStorage.setItem(`go_proxy_url_${provider}`, val);
    }
  };

  const handleProviderChange = (player: 'B' | 'W', provider: AiConfig['provider']) => {
    const savedKey = localStorage.getItem(`go_api_key_${provider}`) || '';
    const savedProxy = localStorage.getItem(`go_proxy_url_${provider}`) || '';
    
    if (player === 'B') {
      setBlackProvider(provider);
      setBlackKey(savedKey);
      setBlackProxyUrl(savedProxy);
      setBlackKeyStatus({ loading: false, message: '', success: null });
      if (provider === 'gemini') setBlackModel('gemini-2.5-flash');
      else if (provider === 'openai') setBlackModel('gpt-4o-mini');
      else if (provider === 'anthropic') setBlackModel('claude-3-5-haiku-latest');
      else if (provider === 'groq') setBlackModel('llama-3.3-70b-versatile');
      else if (provider === 'openrouter') setBlackModel('meta-llama/llama-3-8b-instruct:free');
      else setBlackModel('');
    } else {
      setWhiteProvider(provider);
      setWhiteKey(savedKey);
      setWhiteProxyUrl(savedProxy);
      setWhiteKeyStatus({ loading: false, message: '', success: null });
      if (provider === 'gemini') setWhiteModel('gemini-2.5-flash');
      else if (provider === 'openai') setWhiteModel('gpt-4o-mini');
      else if (provider === 'anthropic') setWhiteModel('claude-3-5-haiku-latest');
      else if (provider === 'groq') setWhiteModel('llama-3.3-70b-versatile');
      else if (provider === 'openrouter') setWhiteModel('meta-llama/llama-3-8b-instruct:free');
      else setWhiteModel('');
    }
  };

  const handleStart = () => {
    onStartGame({
      boardSize,
      rules,
      handicap,
      komi,
      blackPlayer: {
        type: blackType,
        aiConfig: { 
          provider: blackProvider, 
          model: blackModel, 
          apiKey: blackKey, 
          customProxyUrl: blackProxyUrl.trim() || undefined 
        }
      },
      whitePlayer: {
        type: whiteType,
        aiConfig: { 
          provider: whiteProvider, 
          model: whiteModel, 
          apiKey: whiteKey, 
          customProxyUrl: whiteProxyUrl.trim() || undefined 
        }
      }
    });
  };

  // Get current handicap point coordinates for the mini preview
  const handicapPoints = getHandicapPoints(boardSize, handicap);

  return (
    <div className="setup-container glass-panel">
      <h2 className="setup-title">圍棋對弈設定</h2>

      {/* 1. Board Size */}
      <div className="setup-section">
        <h3 className="setup-section-title">1. 選擇棋盤大小</h3>
        <div className="setup-grid-sizes">
          {[9, 13, 19].map((size) => (
            <div
              key={size}
              className={`size-btn ${boardSize === size ? 'active' : ''}`}
              onClick={() => {
                setBoardSize(size);
                if (handicap > 0) setHandicap(0); // Reset handicap if changing size to be safe
              }}
            >
              <span className="size-num">{size}x{size}</span>
              <span className="size-desc">
                {size === 9 ? '入門 / 快速對局' : size === 13 ? '中盤戰 / 戰術練習' : '標準圍棋對局'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Rules & Handicap */}
      <div className="setup-section">
        <h3 className="setup-section-title">2. 規則與讓子</h3>
        <div className="setup-rules-handicap">
          <div className="form-group">
            <label className="form-label">對弈規則</label>
            <select
              className="form-select"
              value={rules}
              onChange={(e) => setRules(e.target.value as 'Chinese' | 'Japanese')}
            >
              <option value="Chinese">中國規則 (數子法)</option>
              <option value="Japanese">日本規則 (比目法)</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">讓子數量</label>
            <select
              className="form-select"
              value={handicap}
              onChange={(e) => setHandicap(parseInt(e.target.value, 10))}
            >
              <option value="0">無 (分先 Even Game)</option>
              {[2, 3, 4, 5, 6, 7, 8, 9].map(num => (
                <option key={num} value={num}>讓 {num} 子</option>
              ))}
            </select>
          </div>
        </div>

        {/* Dynamic Handicap Mini Preview */}
        {handicap > 0 && (
          <div className="handicap-preview-wrapper">
            <div className="handicap-preview-header">讓子星位預覽 ({handicap} 子)：</div>
            <div className="mini-grid" style={{ gridTemplateColumns: `repeat(${boardSize === 19 ? 3 : boardSize === 13 ? 3 : 3}, 1fr)` }}>
              {/* Simplify to a 3x3 layout of star points for easy viewing */}
              {Array.from({ length: 9 }).map((_, i) => {
                // Map indices to 3x3 grid coordinates
                const xMap = [0, 0, 0, 1, 1, 1, 2, 2, 2];
                const yMap = [0, 1, 2, 0, 1, 2, 0, 1, 2];
                
                const low = boardSize === 19 ? 3 : boardSize === 13 ? 3 : 2;
                const mid = boardSize === 19 ? 9 : boardSize === 13 ? 6 : 4;
                const high = boardSize === 19 ? 15 : boardSize === 13 ? 9 : 6;

                const getVal = (idx: number) => idx === 0 ? low : idx === 1 ? mid : high;
                const pt = { x: getVal(xMap[i]), y: getVal(yMap[i]) };

                // Do not show middle star point for 9x9 if not 5/9 stones, etc.
                const isHandicapPlaced = handicapPoints.some(hp => hp.x === pt.x && hp.y === pt.y);

                return (
                  <div 
                    key={i} 
                    className={`mini-cell star-point ${isHandicapPlaced ? 'placed-handicap' : ''}`}
                  />
                );
              })}
            </div>
          </div>
        )}

        <div className="form-group" style={{ marginTop: '1rem' }}>
          <label className="form-label">貼目設定 (Komi)</label>
          <input
            type="number"
            className="form-input"
            step="0.5"
            value={komi}
            onChange={(e) => setKomi(parseFloat(e.target.value))}
          />
        </div>
      </div>

      {/* 3. Player Configurations */}
      <div className="setup-section">
        <h3 className="setup-section-title">3. 玩家與 AI 設定</h3>
        <div className="setup-players">
          
          {/* Black Player Setup */}
          <div className="setup-player-card black-card">
            <div className="player-card-header">
              <span className="stone-dot black" />
              <span>黑方 (Black)</span>
            </div>
            
            <div className="player-mode-toggle">
              <div 
                className={`toggle-option ${blackType === 'human' ? 'active' : ''}`}
                onClick={() => setBlackType('human')}
              >
                手動下棋
              </div>
              <div 
                className={`toggle-option ${blackType === 'ai' ? 'active' : ''}`}
                onClick={() => setBlackType('ai')}
              >
                啟用 AI
              </div>
            </div>

            {blackType === 'ai' && (
              <div className="form-group">
                <label className="form-label">選擇 AI 引擎</label>
                <select
                  className="form-select"
                  value={blackProvider}
                  onChange={(e) => handleProviderChange('B', e.target.value as AiConfig['provider'])}
                >
                  <option value="gemini">Gemini AI (預設)</option>
                  <option value="openai">OpenAI GPT</option>
                  <option value="anthropic">Anthropic Claude</option>
                  <option value="groq">Groq AI (開源超高速)</option>
                  <option value="openrouter">OpenRouter (多種免費模型)</option>
                  <option value="mcts">MCTS 搜尋樹 (內建離線)</option>
                  <option value="local">Local Heuristic (內建離線)</option>
                </select>

                {blackProvider !== 'local' && blackProvider !== 'mcts' && (
                  <>
                    <label className="form-label" style={{ marginTop: '0.5rem' }}>模型型號</label>
                    <select
                      className="form-select"
                      value={blackModel}
                      onChange={(e) => setBlackModel(e.target.value)}
                    >
                      {blackProvider === 'gemini' && (
                        <>
                          <option value="gemini-2.5-flash">gemini-2.5-flash (推薦)</option>
                          <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                        </>
                      )}
                      {blackProvider === 'openai' && (
                        <>
                          <option value="gpt-4o-mini">gpt-4o-mini (推薦)</option>
                          <option value="gpt-4o">gpt-4o</option>
                          <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                        </>
                      )}
                      {blackProvider === 'anthropic' && (
                        <>
                          <option value="claude-3-5-haiku-latest">claude-3-5-haiku-latest (推薦)</option>
                          <option value="claude-3-5-sonnet-latest">claude-3-5-sonnet-latest</option>
                          <option value="claude-3-opus-latest">claude-3-opus-latest</option>
                        </>
                      )}
                      {blackProvider === 'groq' && (
                        <>
                          <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile</option>
                          <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
                          <option value="gemma2-9b-it">gemma2-9b-it</option>
                        </>
                      )}
                      {blackProvider === 'openrouter' && (
                        <>
                          <option value="meta-llama/llama-3-8b-instruct:free">llama-3-8b-instruct (Free)</option>
                          <option value="google/gemma-2-9b-it:free">gemma-2-9b-it (Free)</option>
                        </>
                      )}
                    </select>

                    <div className="api-key-group">
                      <div style={{ marginBottom: '12px' }}>
                        <label className="form-label">自訂代理 API 網址 (選填)</label>
                        <input
                          type="text"
                          placeholder={
                            blackProvider === 'openai'
                              ? '例如：https://your-custom-proxy.com/v1/chat/completions'
                              : blackProvider === 'anthropic'
                              ? '例如：https://your-custom-proxy.com/v1/messages'
                              : '請輸入自訂 API 代理網址'
                          }
                          className="form-input"
                          value={blackProxyUrl}
                          onChange={(e) => handleProxyUrlChange('B', e.target.value)}
                        />
                      </div>

                      <label className="form-label">API 金鑰 (API Key)</label>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                        <input
                          type="password"
                          placeholder="請貼上您的 API 金鑰"
                          className="form-input"
                          style={{ flex: 1, margin: 0 }}
                          value={blackKey}
                          onChange={(e) => handleKeyChange('B', e.target.value)}
                        />
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: '0 16px', fontSize: '13px', whiteSpace: 'nowrap' }}
                          onClick={() => handleVerifyKey('B')}
                          disabled={blackKeyStatus.loading || !blackKey}
                        >
                          {blackKeyStatus.loading ? '驗證中...' : '驗證金鑰'}
                        </button>
                      </div>

                      {blackKeyStatus.message && (
                        <div style={{ 
                          fontSize: '12px', 
                          marginBottom: '8px', 
                          color: blackKeyStatus.success ? '#10b981' : '#f43f5e',
                          background: blackKeyStatus.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                          border: `1px solid ${blackKeyStatus.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                          padding: '6px 10px',
                          borderRadius: '6px'
                        }}>
                          {blackKeyStatus.message}
                        </div>
                      )}

                      <a 
                        href={
                          blackProvider === 'gemini' 
                            ? 'https://aistudio.google.com/' 
                            : blackProvider === 'groq' 
                              ? 'https://console.groq.com/keys' 
                              : blackProvider === 'openai'
                                ? 'https://platform.openai.com/api-keys'
                                : blackProvider === 'anthropic'
                                  ? 'https://console.anthropic.com/'
                                  : 'https://openrouter.ai/keys'
                        } 
                        target="_blank" 
                        rel="noreferrer" 
                        className="api-helper-link"
                      >
                        取得 API 金鑰
                      </a>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* White Player Setup */}
          <div className="setup-player-card white-card">
            <div className="player-card-header">
              <span className="stone-dot white" />
              <span>白方 (White)</span>
            </div>
            
            <div className="player-mode-toggle">
              <div 
                className={`toggle-option ${whiteType === 'human' ? 'active' : ''}`}
                onClick={() => setWhiteType('human')}
              >
                手動下棋
              </div>
              <div 
                className={`toggle-option ${whiteType === 'ai' ? 'active' : ''}`}
                onClick={() => setWhiteType('ai')}
              >
                啟用 AI
              </div>
            </div>

            {whiteType === 'ai' && (
              <div className="form-group">
                <label className="form-label">選擇 AI 引擎</label>
                <select
                  className="form-select"
                  value={whiteProvider}
                  onChange={(e) => handleProviderChange('W', e.target.value as AiConfig['provider'])}
                >
                  <option value="gemini">Gemini AI (預設)</option>
                  <option value="openai">OpenAI GPT</option>
                  <option value="anthropic">Anthropic Claude</option>
                  <option value="groq">Groq AI (開源超高速)</option>
                  <option value="openrouter">OpenRouter (多種免費模型)</option>
                  <option value="mcts">MCTS 搜尋樹 (內建離線)</option>
                  <option value="local">Local Heuristic (內建離線)</option>
                </select>

                {whiteProvider !== 'local' && whiteProvider !== 'mcts' && (
                  <>
                    <label className="form-label" style={{ marginTop: '0.5rem' }}>模型型號</label>
                    <select
                      className="form-select"
                      value={whiteModel}
                      onChange={(e) => setWhiteModel(e.target.value)}
                    >
                      {whiteProvider === 'gemini' && (
                        <>
                          <option value="gemini-2.5-flash">gemini-2.5-flash (推薦)</option>
                          <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                        </>
                      )}
                      {whiteProvider === 'openai' && (
                        <>
                          <option value="gpt-4o-mini">gpt-4o-mini (推薦)</option>
                          <option value="gpt-4o">gpt-4o</option>
                          <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                        </>
                      )}
                      {whiteProvider === 'anthropic' && (
                        <>
                          <option value="claude-3-5-haiku-latest">claude-3-5-haiku-latest (推薦)</option>
                          <option value="claude-3-5-sonnet-latest">claude-3-5-sonnet-latest</option>
                          <option value="claude-3-opus-latest">claude-3-opus-latest</option>
                        </>
                      )}
                      {whiteProvider === 'groq' && (
                        <>
                          <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile</option>
                          <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
                          <option value="gemma2-9b-it">gemma2-9b-it</option>
                        </>
                      )}
                      {whiteProvider === 'openrouter' && (
                        <>
                          <option value="meta-llama/llama-3-8b-instruct:free">llama-3-8b-instruct (Free)</option>
                          <option value="google/gemma-2-9b-it:free">gemma-2-9b-it (Free)</option>
                        </>
                      )}
                    </select>

                    <div className="api-key-group">
                      <div style={{ marginBottom: '12px' }}>
                        <label className="form-label">自訂代理 API 網址 (選填)</label>
                        <input
                          type="text"
                          placeholder={
                            whiteProvider === 'openai'
                              ? '例如：https://your-custom-proxy.com/v1/chat/completions'
                              : whiteProvider === 'anthropic'
                              ? '例如：https://your-custom-proxy.com/v1/messages'
                              : '請輸入自訂 API 代理網址'
                          }
                          className="form-input"
                          value={whiteProxyUrl}
                          onChange={(e) => handleProxyUrlChange('W', e.target.value)}
                        />
                      </div>

                      <label className="form-label">API 金鑰 (API Key)</label>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                        <input
                          type="password"
                          placeholder="請貼上您的 API 金鑰"
                          className="form-input"
                          style={{ flex: 1, margin: 0 }}
                          value={whiteKey}
                          onChange={(e) => handleKeyChange('W', e.target.value)}
                        />
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: '0 16px', fontSize: '13px', whiteSpace: 'nowrap' }}
                          onClick={() => handleVerifyKey('W')}
                          disabled={whiteKeyStatus.loading || !whiteKey}
                        >
                          {whiteKeyStatus.loading ? '驗證中...' : '驗證金鑰'}
                        </button>
                      </div>

                      {whiteKeyStatus.message && (
                        <div style={{ 
                          fontSize: '12px', 
                          marginBottom: '8px', 
                          color: whiteKeyStatus.success ? '#10b981' : '#f43f5e',
                          background: whiteKeyStatus.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
                          border: `1px solid ${whiteKeyStatus.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
                          padding: '6px 10px',
                          borderRadius: '6px'
                        }}>
                          {whiteKeyStatus.message}
                        </div>
                      )}

                      <a 
                        href={
                          whiteProvider === 'gemini' 
                            ? 'https://aistudio.google.com/' 
                            : whiteProvider === 'groq' 
                              ? 'https://console.groq.com/keys' 
                              : whiteProvider === 'openai'
                                ? 'https://platform.openai.com/api-keys'
                                : whiteProvider === 'anthropic'
                                  ? 'https://console.anthropic.com/'
                                  : 'https://openrouter.ai/keys'
                        } 
                        target="_blank" 
                        rel="noreferrer" 
                        className="api-helper-link"
                      >
                        取得 API 金鑰
                      </a>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

        </div>
      </div>

      <button className="btn btn-primary" style={{ width: '100%', padding: '0.85rem' }} onClick={handleStart}>
        開始對弈
      </button>
    </div>
  );
};
