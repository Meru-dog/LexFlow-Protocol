import React from 'react';
import ZKOnboarding from '../components/zk/ZKOnboarding';
import './VerificationPage.css';

const VerificationPage = () => {
    return (
        <div className="verification-page container">
            <div className="verification-header">
                <h1>信頼性検証 (Verification)</h1>
                <p>ゼロ知識証明を用いて、プライバシーを守りながら各種証明を行います。</p>
            </div>

            <ZKOnboarding />

            <div className="verification-footer">
                <p>
                    <small>Powered by Groth16 ZK-SNARKs & SnarkJS</small>
                </p>
            </div>
        </div>
    );
};

export default VerificationPage;
