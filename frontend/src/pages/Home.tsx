import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Zap, Shield, TrendingUp, CheckCircle, ArrowRight } from 'lucide-react';
import './Home.css';

const Home: React.FC = () => {
    return (
        <div className="home">
            {/* Hero Section */}
            <section className="hero">
                <div className="hero-content">
                    <h1 className="hero-title">
                        <span className="gradient-text">LexFlow Protocol</span>
                    </h1>
                    <p className="hero-subtitle">
                        AI駆動のスマートコントラクトプラットフォーム
                    </p>
                    <p className="hero-description">
                        PDF契約書の自動解析、AI による履行判定、<br />
                        弁護士承認、JPYC 自動決済を統合した<br />
                        次世代の契約管理システム
                    </p>
                    <div className="hero-actions">
                        <Link to="/upload" className="btn btn-primary btn-lg">
                            <FileText size={20} />
                            契約書をアップロード
                        </Link>
                        <Link to="/contracts" className="btn btn-secondary btn-lg">
                            契約一覧を見る
                        </Link>
                    </div>
                </div>
                <div className="hero-visual">
                    <div className="floating-card card-1">
                        <FileText size={32} />
                        <span>PDF解析</span>
                    </div>
                    <div className="floating-card card-2">
                        <Zap size={32} />
                        <span>AI判定</span>
                    </div>
                    <div className="floating-card card-3">
                        <Shield size={32} />
                        <span>弁護士承認</span>
                    </div>
                    <div className="floating-card card-4">
                        <TrendingUp size={32} />
                        <span>自動決済</span>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="features">
                <h2 className="section-title">主な機能</h2>
                <div className="features-grid">
                    <div className="feature-card card">
                        <div className="feature-icon">
                            <FileText size={32} />
                        </div>
                        <h3>📄 PDF契約書解析</h3>
                        <p>
                            GPT-4を使用してPDF契約書を自動解析。契約当事者、支払条件、マイルストーン、金額を自動抽出し、構造化データに変換します。
                        </p>
                        <div className="feature-tech">
                            <span className="tech-badge">OpenAI GPT-4</span>
                            <span className="tech-badge">LangChain</span>
                            <span className="tech-badge">PyPDF</span>
                        </div>
                    </div>

                    <div className="feature-card card">
                        <div className="feature-icon">
                            <Zap size={32} />
                        </div>
                        <h3>🤖 AI履行判定</h3>
                        <p>
                            提出された証拠（テキスト、URL、画像）をAIが自動評価。契約条件の達成状況を判定し、信頼度スコアと詳細な理由を提供します。
                        </p>
                        <div className="feature-tech">
                            <span className="tech-badge">GPT-4 Vision</span>
                            <span className="tech-badge">自然言語処理</span>
                            <span className="tech-badge">画像認識</span>
                        </div>
                    </div>

                    <div className="feature-card card">
                        <div className="feature-icon">
                            <Shield size={32} />
                        </div>
                        <h3>⚖️ 弁護士承認フロー</h3>
                        <p>
                            AIの判定を参考に、専門的な法律知識を持つ弁護士が最終判断。人間とAIのハイブリッドアプローチで公正性と正確性を実現します。
                        </p>
                        <div className="feature-tech">
                            <span className="tech-badge">Human-in-the-Loop</span>
                            <span className="tech-badge">多段階承認</span>
                            <span className="tech-badge">監査証跡</span>
                        </div>
                    </div>

                    <div className="feature-card card">
                        <div className="feature-icon">
                            <TrendingUp size={32} />
                        </div>
                        <h3>💰 JPYC自動決済</h3>
                        <p>
                            条件承認後、スマートコントラクトが自動的にJPYC（日本円ステーブルコイン）を送金。エスクロー機能により資金の安全性を保証します。
                        </p>
                        <div className="feature-tech">
                            <span className="tech-badge">Smart Contract</span>
                            <span className="tech-badge">ERC-20</span>
                            <span className="tech-badge">Escrow</span>
                        </div>
                    </div>

                    <div className="feature-card card highlight-zk">
                        <div className="feature-icon">
                            <Shield size={32} />
                        </div>
                        <h3>🛡️ ZK プライバシーオンボーディング</h3>
                        <p>
                            ゼロ知識証明（ZK-Proof）により、個人情報を開示せずにKYCや利益相反チェックを実現。法的な信頼性とプライバシー保護を両立します。
                        </p>
                        <div className="feature-tech">
                            <span className="tech-badge">Circom</span>
                            <span className="tech-badge">snarkjs</span>
                            <span className="tech-badge">Poseidon</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* How It Works Section */}
            <section className="how-it-works">
                <h2 className="section-title">使い方</h2>
                <div className="steps">
                    <div className="step">
                        <div className="step-number">1</div>
                        <div className="step-content">
                            <h3>📄 契約書アップロード</h3>
                            <p>PDF形式の契約書をアップロード。AIが自動的に内容を解析し、重要な情報を抽出します。</p>
                        </div>
                    </div>
                    <div className="step-arrow">→</div>
                    <div className="step">
                        <div className="step-number">2</div>
                        <div className="step-content">
                            <h3>⚙️ 条件設定</h3>
                            <p>支払条件（マイルストーン、納期、承認条件）を設定。AIが検出した条件を編集・追加できます。</p>
                        </div>
                    </div>
                    <div className="step-arrow">→</div>
                    <div className="step">
                        <div className="step-number">3</div>
                        <div className="step-content">
                            <h3>🔐 契約有効化</h3>
                            <p>ブロックチェーン上に契約を登録し、JPYCをエスクローにロック。資金の安全性を確保します。</p>
                        </div>
                    </div>
                    <div className="step-arrow">→</div>
                    <div className="step">
                        <div className="step-number">4</div>
                        <div className="step-content">
                            <h3>📋 証拠提出</h3>
                            <p>条件達成の証拠（成果物、レポート、画像など）を提出。AIが自動的に評価を開始します。</p>
                        </div>
                    </div>
                    <div className="step-arrow">→</div>
                    <div className="step">
                        <div className="step-number">5</div>
                        <div className="step-content">
                            <h3>👨‍⚖️ 弁護士判定</h3>
                            <p>AIの評価を参考に、弁護士が最終判断。承認されると自動的に支払いが実行されます。</p>
                        </div>
                    </div>
                    <div className="step-arrow">→</div>
                    <div className="step">
                        <div className="step-number">6</div>
                        <div className="step-content">
                            <h3>✅ 自動決済</h3>
                            <p>スマートコントラクトがJPYCを自動送金。すべての履歴がブロックチェーンに記録されます。</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Benefits Section */}
            <section className="benefits">
                <h2 className="section-title">なぜLexFlowなのか？</h2>
                <div className="benefits-grid">
                    <div className="benefit-card">
                        <CheckCircle size={24} className="benefit-icon" />
                        <h4>透明性</h4>
                        <p>すべての取引がブロックチェーンに記録され、誰でも検証可能</p>
                    </div>
                    <div className="benefit-card">
                        <CheckCircle size={24} className="benefit-icon" />
                        <h4>自動化</h4>
                        <p>AIと人間の協働により、契約プロセスを効率化</p>
                    </div>
                    <div className="benefit-card">
                        <CheckCircle size={24} className="benefit-icon" />
                        <h4>安全性</h4>
                        <p>エスクロー機能により資金の安全性を保証</p>
                    </div>
                    <div className="benefit-card">
                        <CheckCircle size={24} className="benefit-icon" />
                        <h4>信頼性</h4>
                        <p>弁護士による最終承認で法的な正当性を確保</p>
                    </div>
                    <div className="benefit-card">
                        <CheckCircle size={24} className="benefit-icon" />
                        <h4>効率性</h4>
                        <p>手動処理を削減し、決済までの時間を大幅に短縮</p>
                    </div>
                    <div className="benefit-card">
                        <CheckCircle size={24} className="benefit-icon" />
                        <h4>監査可能</h4>
                        <p>完全な監査証跡により、コンプライアンスを強化</p>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="cta">
                <div className="cta-content">
                    <h2>今すぐ始めましょう</h2>
                    <p>LexFlow Protocolで契約管理を次のレベルへ</p>
                    <Link to="/upload" className="btn btn-primary btn-lg">
                        契約書をアップロード
                        <ArrowRight size={20} />
                    </Link>
                </div>
            </section>
        </div>
    );
};

export default Home;
