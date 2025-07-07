import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AuthScreen from './screens/AuthScreen.tsx';
import MainMenuScreen from './screens/MainMenuScreen.tsx';
import RegisterScreen from './screens/RegisterScreen.tsx';
import ListScreen from './screens/ListScreen.tsx';
import ManagementScreen from './screens/ManagementScreen.tsx';
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

  const login = async (facilityCode: string, password: string) => {
    try {
      // TODO: 実際のAPI呼び出しに置換
      const response = await fetch('http://172.23.33.64:8000/auth/token', {
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
        // TODO: トークンを保存
      } else {
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