import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthScreen from './screens/AuthScreen.tsx';
import MainMenuScreen from './screens/MainMenuScreen.tsx';
import RegisterScreen from './screens/RegisterScreen.tsx';
import ListScreen from './screens/ListScreen.tsx';
import ManagementScreen from './screens/ManagementScreen.tsx';
import { API_ENDPOINTS } from './config/api.ts';
import './App.css';

interface AuthContextType {
  isAuthenticated: boolean;
  facilityName: string;
  login: (facilityCode: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = React.createContext<AuthContextType>({
  isAuthenticated: false,
  facilityName: '',
  login: async () => {},
  logout: () => {},
});

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [facilityName, setFacilityName] = useState('');
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'error'>('checking');

  // バックエンドサーバーの接続確認
  useEffect(() => {
    const checkBackendConnection = async () => {
      const maxRetries = 5;
      let retryCount = 0;
      
      const attemptConnection = async () => {
        try {
          console.log(`Checking backend connection... (attempt ${retryCount + 1}/${maxRetries})`);
          
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 10000);
          
          const response = await fetch(`${API_ENDPOINTS.AUTH_TOKEN.replace('/auth/token', '')}/`, {
            method: 'GET',
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            console.log('Backend server is running');
            setBackendStatus('connected');
            return true;
          } else {
            console.error('Backend server responded with error:', response.status);
            return false;
          }
        } catch (error) {
          console.error(`Backend connection attempt ${retryCount + 1} failed:`, error);
          return false;
        }
      };
      
      while (retryCount < maxRetries) {
        const success = await attemptConnection();
        if (success) {
          return;
        }
        
        retryCount++;
        if (retryCount < maxRetries) {
          console.log(`Retrying in 2 seconds... (${retryCount}/${maxRetries})`);
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }
      
      console.error('All connection attempts failed');
      setBackendStatus('error');
    };

    checkBackendConnection();
  }, []);

  const login = async (facilityCode: string, password: string) => {
    try {
      console.log('Attempting to connect to:', API_ENDPOINTS.AUTH_TOKEN);
      
      const response = await fetch(API_ENDPOINTS.AUTH_TOKEN, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ facility_code: facilityCode, password }),
      });

      if (response.ok) {
        const data = await response.json();
        setIsAuthenticated(true);
        setFacilityName(`施設: ${facilityCode}`);
        console.log('Login successful');
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Login failed:', errorData);
        throw new Error('認証に失敗しました');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setFacilityName('');
  };

  // バックエンド接続エラー時の表示
  if (backendStatus === 'error') {
    return (
      <div style={{ 
        padding: '20px', 
        textAlign: 'center',
        fontFamily: 'Arial, sans-serif'
      }}>
        <h2>バックエンドサーバーに接続できません</h2>
        <p>アプリケーションを再起動してください。</p>
        <p>エラー詳細は開発者ツールのコンソールを確認してください。</p>
        <button 
          onClick={() => window.location.reload()}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          再読み込み
        </button>
      </div>
    );
  }

  // 接続確認中
  if (backendStatus === 'checking') {
    return (
      <div style={{ 
        padding: '20px', 
        textAlign: 'center',
        fontFamily: 'Arial, sans-serif'
      }}>
        <h2>バックエンドサーバーに接続中...</h2>
        <p>しばらくお待ちください。</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, facilityName, login, logout }}>
      <Router>
        <div className="App">
          <Routes>
            <Route 
              path="/" 
              element={isAuthenticated ? <Navigate to="/menu" /> : <AuthScreen />} 
            />
            <Route 
              path="/menu" 
              element={isAuthenticated ? <MainMenuScreen /> : <Navigate to="/" />} 
            />
            <Route 
              path="/register" 
              element={isAuthenticated ? <RegisterScreen /> : <Navigate to="/" />} 
            />
            <Route 
              path="/list" 
              element={isAuthenticated ? <ListScreen /> : <Navigate to="/" />} 
            />
            <Route 
              path="/management" 
              element={isAuthenticated ? <ManagementScreen /> : <Navigate to="/" />} 
            />
          </Routes>
        </div>
      </Router>
    </AuthContext.Provider>
  );
}

export default App; 