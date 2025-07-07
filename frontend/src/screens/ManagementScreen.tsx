import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface Item {
  item_id: string;
  facility_id: number;
  found_datetime: string;
  accepted_datetime: string;
  found_place: string;
  category_large: string;
  category_medium: string;
  name: string;
  features: string;
  color: string;
  status: string;
  image_url: string;
  finder_type: string;
  claims_ownership: boolean;
  claims_reward: boolean;
  storage_location: string;
  created_at: string;
  updated_at: string;
}

interface Statistics {
  total: number;
  inStorage: number;
  returned: number;
  disposed: number;
  expiringSoon: number;
  expired: number;
  byCategory: { [key: string]: number };
  byMonth: { [key: string]: number };
}

const ManagementScreen: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [showExpiredOnly, setShowExpiredOnly] = useState(false);
  const [showExpiringSoon, setShowExpiringSoon] = useState(false);
  const [bulkAction, setBulkAction] = useState<string>('');
  const [processing, setProcessing] = useState(false);

  // 初期データ読み込み
  useEffect(() => {
    fetchItems();
  }, []);

  // 統計情報の計算
  useEffect(() => {
    if (items.length > 0) {
      calculateStatistics();
    }
  }, [items]);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8000/items');
      setItems(response.data);
    } catch (error) {
      console.error('データ取得エラー:', error);
      alert('データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const calculateStatistics = () => {
    const now = new Date();
    const threeMonthsFromNow = new Date(now.getTime() + 3 * 30 * 24 * 60 * 60 * 1000);
    
    const stats: Statistics = {
      total: items.length,
      inStorage: items.filter(item => item.status === '保管中').length,
      returned: items.filter(item => item.status === '返還済み').length,
      disposed: items.filter(item => item.status === '廃棄済み').length,
      expiringSoon: 0,
      expired: 0,
      byCategory: {},
      byMonth: {},
    };

    // 保管期限の計算（拾得から3ヶ月）
    items.forEach(item => {
      const foundDate = new Date(item.found_datetime);
      const expirationDate = new Date(foundDate.getTime() + 3 * 30 * 24 * 60 * 60 * 1000);
      
      if (expirationDate < now) {
        stats.expired++;
      } else if (expirationDate < threeMonthsFromNow) {
        stats.expiringSoon++;
      }

      // カテゴリ別統計
      const category = item.category_large;
      stats.byCategory[category] = (stats.byCategory[category] || 0) + 1;

      // 月別統計
      const month = foundDate.toISOString().slice(0, 7); // YYYY-MM
      stats.byMonth[month] = (stats.byMonth[month] || 0) + 1;
    });

    setStatistics(stats);
  };

  const getExpirationDate = (foundDateTime: string) => {
    const foundDate = new Date(foundDateTime);
    return new Date(foundDate.getTime() + 3 * 30 * 24 * 60 * 60 * 1000);
  };

  const getDaysUntilExpiration = (foundDateTime: string) => {
    const expirationDate = getExpirationDate(foundDateTime);
    const now = new Date();
    const diffTime = expirationDate.getTime() - now.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const getExpirationStatus = (foundDateTime: string) => {
    const days = getDaysUntilExpiration(foundDateTime);
    if (days < 0) return { status: 'expired', text: '期限切れ', color: 'text-red-600' };
    if (days <= 30) return { status: 'expiring', text: `${days}日後`, color: 'text-orange-600' };
    return { status: 'ok', text: `${days}日後`, color: 'text-green-600' };
  };

  const handleBulkAction = async () => {
    if (!bulkAction || selectedItems.length === 0) {
      alert('操作と対象アイテムを選択してください');
      return;
    }

    if (!confirm(`${selectedItems.length}件のアイテムを${bulkAction}しますか？`)) {
      return;
    }

    setProcessing(true);
    try {
      for (const itemId of selectedItems) {
        const item = items.find(i => i.item_id === itemId);
        if (item) {
          const updateData = { ...item };
          
          switch (bulkAction) {
            case '返還済み':
              updateData.status = '返還済み';
              break;
            case '廃棄済み':
              updateData.status = '廃棄済み';
              break;
            case '保管中':
              updateData.status = '保管中';
              break;
          }
          
          await axios.put(`http://localhost:8000/items/${itemId}`, updateData);
        }
      }
      
      alert(`${selectedItems.length}件のアイテムを${bulkAction}に更新しました`);
      setSelectedItems([]);
      setBulkAction('');
      fetchItems();
      
    } catch (error) {
      console.error('一括更新エラー:', error);
      alert('一括更新に失敗しました');
    } finally {
      setProcessing(false);
    }
  };

  const toggleItemSelection = (itemId: string) => {
    setSelectedItems(prev => 
      prev.includes(itemId) 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const toggleAllItems = () => {
    const filteredItems = getFilteredItems();
    if (selectedItems.length === filteredItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(filteredItems.map(item => item.item_id));
    }
  };

  const getFilteredItems = () => {
    let filtered = items;
    
    if (showExpiredOnly) {
      filtered = filtered.filter(item => getDaysUntilExpiration(item.found_datetime) < 0);
    }
    
    if (showExpiringSoon) {
      filtered = filtered.filter(item => {
        const days = getDaysUntilExpiration(item.found_datetime);
        return days >= 0 && days <= 30;
      });
    }
    
    return filtered;
  };

  const formatDateTime = (dateTimeStr: string) => {
    return new Date(dateTimeStr).toLocaleString('ja-JP');
  };

  const filteredItems = getFilteredItems();

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      <div className="w-full max-w-7xl h-[90vh] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden">
        <header className="bg-gray-800 text-white p-4 flex justify-between items-center shadow-md">
          <h1 className="text-xl font-bold">拾得物管理システム</h1>
        </header>
        
        <main className="flex-grow overflow-y-auto">
          <div className="p-6 md:p-8">
            <button
              onClick={() => navigate('/menu')}
              className="mb-6 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-gray-600 hover:bg-gray-700"
            >
              ← メインメニューへ
            </button>
            
            <h2 className="text-2xl font-bold text-gray-800 mb-6">保管期限管理</h2>

            {/* 統計情報 */}
            {statistics && (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{statistics.total}</div>
                  <div className="text-sm text-gray-600">総件数</div>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{statistics.inStorage}</div>
                  <div className="text-sm text-gray-600">保管中</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{statistics.returned}</div>
                  <div className="text-sm text-gray-600">返還済み</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{statistics.disposed}</div>
                  <div className="text-sm text-gray-600">廃棄済み</div>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">{statistics.expiringSoon}</div>
                  <div className="text-sm text-gray-600">期限間近</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{statistics.expired}</div>
                  <div className="text-sm text-gray-600">期限切れ</div>
                </div>
              </div>
            )}

            {/* フィルター・操作 */}
            <div className="bg-gray-50 p-4 rounded-lg mb-6">
              <div className="flex flex-wrap items-center gap-4 mb-4">
                <div className="flex items-center space-x-4">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={showExpiredOnly}
                      onChange={(e) => setShowExpiredOnly(e.target.checked)}
                      className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">期限切れのみ</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={showExpiringSoon}
                      onChange={(e) => setShowExpiringSoon(e.target.checked)}
                      className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-700">期限間近のみ</span>
                  </label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-700">一括操作:</span>
                  <select
                    value={bulkAction}
                    onChange={(e) => setBulkAction(e.target.value)}
                    className="px-3 py-1 border border-gray-300 rounded-md text-sm"
                  >
                    <option value="">選択してください</option>
                    <option value="返還済み">返還済み</option>
                    <option value="廃棄済み">廃棄済み</option>
                    <option value="保管中">保管中</option>
                  </select>
                  <button
                    onClick={handleBulkAction}
                    disabled={processing || !bulkAction || selectedItems.length === 0}
                    className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    {processing ? '処理中...' : '実行'}
                  </button>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  表示件数: {filteredItems.length}件
                  {selectedItems.length > 0 && (
                    <span className="ml-2 text-blue-600">
                      (選択中: {selectedItems.length}件)
                    </span>
                  )}
                </div>
                <button
                  onClick={fetchItems}
                  className="px-3 py-1 bg-gray-600 text-white rounded-md text-sm hover:bg-gray-700"
                >
                  更新
                </button>
              </div>
            </div>

            {/* アイテム一覧 */}
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="text-gray-500">読み込み中...</div>
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">表示するアイテムがありません</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white border border-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left">
                        <input
                          type="checkbox"
                          checked={selectedItems.length === filteredItems.length && filteredItems.length > 0}
                          onChange={toggleAllItems}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        管理番号
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        品名
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        状態
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        拾得日
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        保管期限
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        保管場所
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredItems.map((item) => {
                      const expirationStatus = getExpirationStatus(item.found_datetime);
                      return (
                        <tr key={item.item_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={selectedItems.includes(item.item_id)}
                              onChange={() => toggleItemSelection(item.item_id)}
                              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            />
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {item.item_id}
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-sm font-medium text-gray-900">{item.name}</div>
                            <div className="text-sm text-gray-500">{item.category_large}</div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              item.status === '保管中' ? 'bg-blue-100 text-blue-800' :
                              item.status === '返還済み' ? 'bg-green-100 text-green-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {item.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {formatDateTime(item.found_datetime)}
                          </td>
                          <td className="px-4 py-3">
                            <div className={`text-sm font-medium ${expirationStatus.color}`}>
                              {expirationStatus.text}
                            </div>
                            <div className="text-xs text-gray-500">
                              {getExpirationDate(item.found_datetime).toLocaleDateString('ja-JP')}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {item.storage_location}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* カテゴリ別統計 */}
            {statistics && Object.keys(statistics.byCategory).length > 0 && (
              <div className="mt-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">カテゴリ別統計</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(statistics.byCategory)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 8)
                    .map(([category, count]) => (
                      <div key={category} className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-lg font-semibold text-gray-800">{count}</div>
                        <div className="text-sm text-gray-600 truncate">{category}</div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default ManagementScreen; 