import React, { useState, useContext } from 'react';
import { AuthContext } from '../App.tsx';

const AuthScreen: React.FC = () => {
  const [facilityCode, setFacilityCode] = useState('FACILITY-01');
  const [password, setPassword] = useState('password');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const { login } = useContext(AuthContext);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await login(facilityCode, password);
    } catch (err) {
      setError('認証に失敗しました。施設コードとパスワードを確認してください。');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      <div className="w-full max-w-7xl h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
        <header className="bg-gray-800 text-white p-4 flex justify-between items-center shadow-md">
          <h1 className="text-xl font-bold">拾得物管理システム</h1>
        </header>
        
        <main className="flex-grow overflow-y-auto">
          <div className="flex flex-col items-center justify-center h-full p-8 bg-gray-50">
            <div className="w-full max-w-sm p-8 bg-white rounded-lg shadow-md">
              <h2 className="text-2xl font-bold text-center text-gray-700 mb-6">施設認証</h2>
              
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label htmlFor="facility-code" className="block text-gray-700 text-sm font-bold mb-2">
                    施設コード
                  </label>
                  <input
                    type="text"
                    id="facility-code"
                    value={facilityCode}
                    onChange={(e) => setFacilityCode(e.target.value)}
                    className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                <div className="mb-6">
                  <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">
                    パスワード
                  </label>
                  <input
                    type="password"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="shadow appearance-none border rounded-lg w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>
                
                {error && (
                  <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
                    {error}
                  </div>
                )}
                
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-bold py-2 px-4 rounded-lg focus:outline-none focus:shadow-outline transition-colors"
                >
                  {isLoading ? '認証中...' : '認証'}
                </button>
              </form>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AuthScreen; 