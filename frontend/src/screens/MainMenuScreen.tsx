import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../App.tsx';

const MainMenuScreen: React.FC = () => {
  const navigate = useNavigate();
  const { facilityName, logout } = useContext(AuthContext);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      <div className="w-full max-w-7xl h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
        <header className="bg-gray-800 text-white p-4 flex justify-between items-center shadow-md">
          <h1 className="text-xl font-bold">拾得物管理システム</h1>
          <div className="text-right">
            <p className="font-semibold">{facilityName}</p>
            <button
              onClick={handleLogout}
              className="text-sm text-red-400 hover:text-red-300"
            >
              × ログアウト
            </button>
          </div>
        </header>
        
        <main className="flex-grow overflow-y-auto">
          <div className="flex flex-col items-center justify-center h-full p-8 bg-gray-50">
            <h2 className="text-3xl font-bold text-gray-800 mb-10">メインメニュー</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-4xl">
              <button
                onClick={() => navigate('/register')}
                className="group flex flex-col items-center justify-center p-8 bg-white rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all"
              >
                <svg
                  className="w-16 h-16 text-blue-500 mb-4 group-hover:text-blue-600 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-xl font-bold text-gray-700">新規拾得物登録</span>
                <p className="text-gray-500 mt-1 text-center">新しい拾得物を登録します。</p>
              </button>
              
              <button
                onClick={() => navigate('/list')}
                className="group flex flex-col items-center justify-center p-8 bg-white rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all"
              >
                <svg
                  className="w-16 h-16 text-green-500 mb-4 group-hover:text-green-600 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 10h16M4 14h16M4 18h16"
                  />
                </svg>
                <span className="text-xl font-bold text-gray-700">拾得物一覧・検索</span>
                <p className="text-gray-500 mt-1 text-center">登録済みの拾得物を検索・管理します。</p>
              </button>
              
              <button
                onClick={() => navigate('/management')}
                className="group flex flex-col items-center justify-center p-8 bg-white rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all"
              >
                <svg
                  className="w-16 h-16 text-purple-500 mb-4 group-hover:text-purple-600 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <span className="text-xl font-bold text-gray-700">保管期限管理</span>
                <p className="text-gray-500 mt-1 text-center">期限が経過した物品を処理します。</p>
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default MainMenuScreen; 