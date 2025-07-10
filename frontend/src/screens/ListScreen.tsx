import React, { useState, useEffect, useRef } from 'react';
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

interface SearchFilters {
  keywords: string;
  found_place: string;
  date_from: string;
  date_to: string;
  semantic_search: boolean;
}

const ListScreen: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [filters, setFilters] = useState<SearchFilters>({
    keywords: '',
    found_place: '',
    date_from: '',
    date_to: '',
    semantic_search: false,
  });

  // 初期データ読み込み
  useEffect(() => {
    fetchItems();
  }, []);

  const fetchItems = async (searchParams?: SearchFilters) => {
    setLoading(true);
    try {
      let url = 'http://localhost:8000/items';
      const params = new URLSearchParams();
      
      if (searchParams) {
        if (searchParams.keywords) params.append('keywords', searchParams.keywords);
        if (searchParams.found_place) params.append('found_place', searchParams.found_place);
        if (searchParams.date_from) params.append('date_from', searchParams.date_from);
        if (searchParams.date_to) params.append('date_to', searchParams.date_to);
        if (searchParams.semantic_search) params.append('semantic_search', 'true');
      }
      
      if (params.toString()) {
        url += '?' + params.toString();
      }
      
      const response = await axios.get(url);
      setItems(response.data);
    } catch (error) {
      console.error('データ取得エラー:', error);
      alert('データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    setSearching(true);
    try {
      await fetchItems(filters);
    } finally {
      setSearching(false);
    }
  };

  const handleFilterChange = (field: keyof SearchFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const clearFilters = () => {
    setFilters({
      keywords: '',
      found_place: '',
      date_from: '',
      date_to: '',
      semantic_search: false,
    });
    fetchItems();
  };

  const formatDateTime = (dateTimeStr: string) => {
    return new Date(dateTimeStr).toLocaleString('ja-JP');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case '保管中':
        return 'bg-blue-100 text-blue-800';
      case '返還済み':
        return 'bg-green-100 text-green-800';
      case '廃棄済み':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    const colors = [
      'bg-purple-100 text-purple-800',
      'bg-indigo-100 text-indigo-800',
      'bg-blue-100 text-blue-800',
      'bg-green-100 text-green-800',
      'bg-yellow-100 text-yellow-800',
      'bg-red-100 text-red-800',
      'bg-pink-100 text-pink-800',
    ];
    const index = category.charCodeAt(0) % colors.length;
    return colors[index];
  };

  // 画像アップロード処理
  const handleImageUpload = async (itemId: string, file: File) => {
    setUploading(true);
    try {
      // 現在の日時からファイル名を生成（yyyymmdd_nnnn形式）
      const now = new Date();
      const datePart = now.getFullYear().toString() + 
                     (now.getMonth() + 1).toString().padStart(2, '0') + 
                     now.getDate().toString().padStart(2, '0');
      
      // 拡張子を取得
      const originalExt = file.name.split('.').pop()?.toLowerCase();
      const ext = originalExt && ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(originalExt) 
                 ? `.${originalExt}` : '.jpg';
      
      // 同日の通し番号は後でサーバー側で決定されるため、一時的な名前を使用
      const tempFileName = `${datePart}_temp${ext}`;
      
      // 新しいFileオブジェクトを作成（元のファイルの内容、新しい名前）
      const renamedFile = new File([file], tempFileName, { type: file.type });
      
      const formData = new FormData();
      formData.append('file', renamedFile);
      // 画像アップロード用APIエンドポイント
      await axios.post(`http://localhost:8000/items/${itemId}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      alert('画像を追加しました');
      setSelectedItem(null);
      fetchItems();
    } catch (error) {
      console.error('画像アップロードエラー:', error);
      alert('画像の追加に失敗しました');
    } finally {
      setUploading(false);
    }
  };

  // 画像URL補正関数
  const getImageUrl = (url: string) => {
    if (!url) return '';
    if (url.startsWith('http')) return url + '?t=' + new Date().getTime();
    if (url.startsWith('/static/')) return `http://localhost:8000${url}?t=${new Date().getTime()}`;
    if (url.startsWith('data:')) return url;
    return '';
  };

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
            
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-800">拾得物一覧・検索</h2>
              <div className="flex space-x-2">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  {showFilters ? 'フィルター非表示' : 'フィルター表示'}
                </button>
                <button
                  onClick={() => fetchItems()}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  全件表示
                </button>
              </div>
            </div>

            {/* 検索フィルター */}
            {showFilters && (
              <div className="bg-gray-50 p-6 rounded-lg mb-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">検索条件</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      キーワード検索
                    </label>
                    <input
                      type="text"
                      value={filters.keywords}
                      onChange={(e) => handleFilterChange('keywords', e.target.value)}
                      placeholder="品名・特徴（スペース区切り）"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      拾得場所
                    </label>
                    <input
                      type="text"
                      value={filters.found_place}
                      onChange={(e) => handleFilterChange('found_place', e.target.value)}
                      placeholder="例: 1階ロビー"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      拾得日（開始）
                    </label>
                    <input
                      type="date"
                      value={filters.date_from}
                      onChange={(e) => handleFilterChange('date_from', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      拾得日（終了）
                    </label>
                    <input
                      type="date"
                      value={filters.date_to}
                      onChange={(e) => handleFilterChange('date_to', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="semantic_search"
                      checked={filters.semantic_search}
                      onChange={(e) => handleFilterChange('semantic_search', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="semantic_search" className="ml-2 block text-sm text-gray-700">
                      セマンティック検索
                    </label>
                  </div>
                </div>
                
                <div className="flex space-x-2">
                  <button
                    onClick={handleSearch}
                    disabled={searching}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    {searching ? '検索中...' : '検索実行'}
                  </button>
                  <button
                    onClick={clearFilters}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  >
                    条件クリア
                  </button>
                </div>
              </div>
            )}

            {/* 結果件数 */}
            <div className="mb-4">
              <p className="text-gray-600">
                検索結果: <span className="font-semibold">{items.length}</span>件
              </p>
            </div>

            {/* アイテム一覧 */}
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="text-gray-500">読み込み中...</div>
              </div>
            ) : items.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">拾得物が見つかりませんでした</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {items.map((item) => (
                  <div
                    key={item.item_id}
                    className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => setSelectedItem(item)}
                  >
                    {/* 画像 */}
                    <div className="h-48 bg-gray-100 rounded-t-lg flex items-center justify-center overflow-hidden">
                      {item.image_url ? (
                        <img
                          src={getImageUrl(item.image_url)}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="text-gray-400">画像なし</div>
                      )}
                    </div>
                    
                    {/* 情報 */}
                    <div className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-semibold text-gray-800 truncate">{item.name}</h3>
                        <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(item.status)}`}>
                          {item.status}
                        </span>
                      </div>
                      
                      <div className="space-y-1 text-sm text-gray-600">
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 text-xs rounded-full ${getCategoryColor(item.category_large)}`}>
                            {item.category_large}
                          </span>
                          <span className="text-gray-500">•</span>
                          <span>{item.color}</span>
                        </div>
                        
                        <div className="truncate">{item.features}</div>
                        <div>拾得場所: {item.found_place}</div>
                        <div>拾得日時: {formatDateTime(item.found_datetime)}</div>
                        <div>保管場所: {item.storage_location}</div>
                        
                        {(item.claims_ownership || item.claims_reward) && (
                          <div className="flex space-x-2 mt-2">
                            {item.claims_ownership && (
                              <span className="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded-full">
                                所有権主張
                              </span>
                            )}
                            {item.claims_reward && (
                              <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">
                                報酬要求
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

        {/* 詳細モーダル */}
        {selectedItem && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold text-gray-800">{selectedItem.name}</h3>
                  <button
                    onClick={() => setSelectedItem(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* 画像 */}
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">画像</h4>
                    <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden mb-2">
                      {selectedItem.image_url ? (
                        <img
                          src={getImageUrl(selectedItem.image_url)}
                          alt={selectedItem.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="text-gray-400">画像なし</div>
                      )}
                    </div>
                    {/* 画像追加ボタン（画像が未登録の場合のみ表示） */}
                    {!selectedItem.image_url && (
                      <div className="mt-2">
                        <input
                          type="file"
                          accept="image/*"
                          ref={fileInputRef}
                          style={{ display: 'none' }}
                          onChange={e => {
                            const file = e.target.files?.[0];
                            if (file) {
                              handleImageUpload(selectedItem.item_id, file);
                            }
                          }}
                        />
                        <button
                          type="button"
                          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={uploading}
                        >
                          {uploading ? 'アップロード中...' : '画像を追加'}
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {/* 詳細情報 */}
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold text-gray-800 mb-2">基本情報</h4>
                      <div className="space-y-2 text-sm">
                        <div><span className="font-medium">管理番号:</span> {selectedItem.item_id}</div>
                        <div><span className="font-medium">状態:</span> 
                          <span className={`ml-2 px-2 py-1 text-xs rounded-full ${getStatusColor(selectedItem.status)}`}>
                            {selectedItem.status}
                          </span>
                        </div>
                        <div><span className="font-medium">大分類:</span> {selectedItem.category_large}</div>
                        <div><span className="font-medium">中分類:</span> {selectedItem.category_medium}</div>
                        <div><span className="font-medium">色:</span> {selectedItem.color}</div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-semibold text-gray-800 mb-2">拾得情報</h4>
                      <div className="space-y-2 text-sm">
                        <div><span className="font-medium">拾得場所:</span> {selectedItem.found_place}</div>
                        <div><span className="font-medium">拾得日時:</span> {formatDateTime(selectedItem.found_datetime)}</div>
                        <div><span className="font-medium">受付日時:</span> {formatDateTime(selectedItem.accepted_datetime)}</div>
                        <div><span className="font-medium">拾得者種別:</span> {selectedItem.finder_type}</div>
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="font-semibold text-gray-800 mb-2">特徴・詳細</h4>
                      <p className="text-sm text-gray-600">{selectedItem.features}</p>
                    </div>
                    
                    <div>
                      <h4 className="font-semibold text-gray-800 mb-2">保管情報</h4>
                      <div className="space-y-2 text-sm">
                        <div><span className="font-medium">保管場所:</span> {selectedItem.storage_location}</div>
                        <div><span className="font-medium">登録日時:</span> {formatDateTime(selectedItem.created_at)}</div>
                        <div><span className="font-medium">更新日時:</span> {formatDateTime(selectedItem.updated_at)}</div>
                      </div>
                    </div>
                    
                    {(selectedItem.claims_ownership || selectedItem.claims_reward) && (
                      <div>
                        <h4 className="font-semibold text-gray-800 mb-2">所有権・報酬</h4>
                        <div className="space-y-2 text-sm">
                          {selectedItem.claims_ownership && (
                            <div className="flex items-center">
                              <span className="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded-full mr-2">
                                所有権主張
                              </span>
                              <span>拾得者が所有権を主張</span>
                            </div>
                          )}
                          {selectedItem.claims_reward && (
                            <div className="flex items-center">
                              <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full mr-2">
                                報酬要求
                              </span>
                              <span>拾得者が報酬を要求</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex justify-end mt-6">
                  <button
                    onClick={() => setSelectedItem(null)}
                    className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                  >
                    閉じる
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ListScreen; 