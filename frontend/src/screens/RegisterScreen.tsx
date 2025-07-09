import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface RecognizeResponse {
  category_large: string;
  category_medium: string;
  name: string;
  features: string;
  color: string;
  confidence: number;
}

interface ItemForm {
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
}

const RegisterScreen: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [recognizedData, setRecognizedData] = useState<RecognizeResponse | null>(null);
  const [imageSource, setImageSource] = useState<'file' | 'camera' | 'none'>('none');
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  
  // videoRefの初期化確認
  useEffect(() => {
    console.log('videoRef初期化確認:', { current: !!videoRef.current });
  }, []);
  
  // JSTの現在時刻をdatetime-local用の文字列で取得
  const getJstDatetimeLocal = () => {
    const now = new Date();
    // JSTの各値を取得
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hour = String(now.getHours()).padStart(2, '0');
    const minute = String(now.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hour}:${minute}`;
  };

  const [formData, setFormData] = useState<ItemForm>({
    facility_id: 1,
    found_datetime: '',
    accepted_datetime: getJstDatetimeLocal(),
    found_place: '',
    category_large: '',
    category_medium: '',
    name: '',
    features: '',
    color: '',
    status: '保管中',
    image_url: '',
    finder_type: '一般',
    claims_ownership: false,
    claims_reward: false,
  });

  // 分類データの状態
  const [classifications, setClassifications] = useState<any>({ categories: [] });

  useEffect(() => {
    fetch('./item_classification.json')
      .then(res => res.json())
      .then(data => setClassifications(data))
      .catch(error => {
        console.error('分類データの読み込みに失敗しました:', error);
        // エラー時のフォールバック処理
        setClassifications({ categories: [] });
      });
  }, []);

  const categories = classifications.categories;
  const largeCategoryOptions = categories.map((cat: any) => cat.large_category);
  const mediumCategoryOptions =
    categories.find((cat: any) => cat.large_category === formData.category_large)?.medium_categories.map((m: any) => m.medium_category) || [];

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setImageSource('file');
    }
  };

  const startCamera = async () => {
    try {
      console.log('カメラ起動開始...');
      console.log('videoRef状態:', { current: !!videoRef.current });
      
      console.log('ブラウザ環境:', {
        userAgent: navigator.userAgent,
        mediaDevices: !!navigator.mediaDevices,
        getUserMedia: !!navigator.mediaDevices?.getUserMedia,
        https: window.location.protocol === 'https:',
        localhost: window.location.hostname === 'localhost'
      });
      
      // 既存のストリームがあれば停止
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      
      // カメラ権限の確認
      const permissions = await navigator.permissions.query({ name: 'camera' as PermissionName });
      console.log('カメラ権限状態:', permissions.state);
      
      if (permissions.state === 'denied') {
        throw new Error('カメラアクセスが拒否されています。ブラウザの設定でカメラを許可してください。');
      }
      
      // 利用可能なカメラデバイスを確認
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      console.log('利用可能なカメラデバイス:', videoDevices);
      
      if (videoDevices.length === 0) {
        throw new Error('カメラデバイスが見つかりません。デバイスにカメラが接続されているか確認してください。');
      }
      
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 }, 
          height: { ideal: 480 },
          facingMode: 'environment' // 背面カメラを優先
        } 
      });
      console.log('カメラストリーム取得成功:', mediaStream);
      setStream(mediaStream);
      
      // まずカメラアクティブ状態を設定してビデオ要素を表示
      setIsCameraActive(true);
      setImageSource('camera');
      
      // 少し待ってからvideoRefの準備を待つ
      await new Promise(resolve => setTimeout(resolve, 100));
      
      // videoRefの準備を待つ
      const waitForVideoRef = () => {
        return new Promise<HTMLVideoElement>((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('ビデオ要素の準備がタイムアウトしました'));
          }, 5000); // 5秒タイムアウト
          
          const checkVideoRef = () => {
            if (videoRef.current) {
              clearTimeout(timeout);
              console.log('videoRef準備完了');
              resolve(videoRef.current);
            } else {
              console.log('videoRef待機中...');
              setTimeout(checkVideoRef, 100);
            }
          };
          
          checkVideoRef();
        });
      };
      
      const video = await waitForVideoRef();
      video.srcObject = mediaStream;
      
      // ビデオの準備完了を待つ
      const waitForVideo = () => {
        return new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('ビデオの準備がタイムアウトしました'));
          }, 10000); // 10秒タイムアウト
          
          const checkReady = () => {
            if (video.videoWidth > 0 && video.videoHeight > 0 && video.readyState >= 2) {
              clearTimeout(timeout);
              console.log('ビデオ準備完了:', video.videoWidth, 'x', video.videoHeight);
              resolve();
            } else {
              console.log('ビデオ準備中...', {
                width: video.videoWidth,
                height: video.videoHeight,
                readyState: video.readyState
              });
              setTimeout(checkReady, 100);
            }
          };
          
          video.onloadedmetadata = () => {
            console.log('ビデオメタデータ読み込み完了');
            video.play().then(() => {
              console.log('ビデオ再生開始');
              checkReady();
            }).catch(err => {
              console.error('ビデオ再生エラー:', err);
              reject(err);
            });
          };
          
          video.onerror = (e) => {
            console.error('ビデオエラー:', e);
            clearTimeout(timeout);
            reject(new Error('ビデオエラーが発生しました'));
          };
        });
      };
      
      await waitForVideo();
      console.log('カメラ起動完了');
      
    } catch (error) {
      console.error('カメラ起動エラー:', error);
      
      // エラーが発生した場合はカメラ状態をリセット
      setIsCameraActive(false);
      setImageSource('none');
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
        setStream(null);
      }
      
      let errorMessage = 'カメラへのアクセスに失敗しました。';
      
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage = 'カメラアクセスが拒否されました。ブラウザの設定でカメラを許可してください。';
        } else if (error.name === 'NotFoundError') {
          errorMessage = 'カメラデバイスが見つかりません。デバイスにカメラが接続されているか確認してください。';
        } else if (error.name === 'NotReadableError') {
          errorMessage = 'カメラが他のアプリケーションで使用中です。他のアプリを閉じてから再度お試しください。';
        } else if (error.name === 'OverconstrainedError') {
          errorMessage = '要求されたカメラ設定が利用できません。別のカメラを試してください。';
        } else if (error.name === 'TypeError') {
          errorMessage = 'ブラウザがカメラ機能をサポートしていません。HTTPS環境でアクセスしてください。';
        } else {
          errorMessage = error.message || errorMessage;
        }
      }
      
      // 詳細な解決策を表示
      const solutionMessage = `
${errorMessage}

解決方法:
1. ブラウザのアドレスバー横のカメラアイコンをクリックして「許可」を選択
2. ブラウザの設定 → プライバシーとセキュリティ → サイトの設定 → カメラで許可
3. 他のアプリケーションでカメラを使用している場合は閉じてください
4. HTTPS環境（localhostまたはhttps://）でアクセスしてください
5. デバイスにカメラが接続されているか確認してください

詳細なエラー情報はブラウザのコンソール（F12）で確認できます。
      `;
      
      alert(solutionMessage);
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setIsCameraActive(false);
    setImageSource('none');
  };

  const capturePhoto = () => {
    console.log('写真撮影開始...');
    
    if (!videoRef.current || !canvasRef.current) {
      console.error('videoRefまたはcanvasRefがnullです');
      alert('カメラの初期化に失敗しました');
      return;
    }
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    console.log('ビデオ状態:', {
      videoWidth: video.videoWidth,
      videoHeight: video.videoHeight,
      readyState: video.readyState,
      paused: video.paused,
      ended: video.ended
    });
    
    if (!context) {
      console.error('キャンバスコンテキストの取得に失敗しました');
      alert('写真の撮影に失敗しました');
      return;
    }
    
    if (video.videoWidth > 0 && video.videoHeight > 0 && video.readyState >= 2) {
      // キャンバスサイズをビデオサイズに合わせる
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      console.log('キャンバスサイズ設定:', canvas.width, 'x', canvas.height);
      
      try {
        // ビデオから画像をキャンバスに描画
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        console.log('キャンバスへの描画完了');
        
        // キャンバスからBlobを生成
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
            setSelectedFile(file);
            setPreviewUrl(URL.createObjectURL(blob));
            stopCamera();
            console.log('写真撮影完了:', file.name, file.size);
            alert('写真の撮影が完了しました！');
          } else {
            console.error('Blob生成に失敗しました');
            alert('写真の撮影に失敗しました');
          }
        }, 'image/jpeg', 0.8);
      } catch (error) {
        console.error('キャンバス描画エラー:', error);
        alert('写真の撮影に失敗しました');
      }
    } else {
      console.error('ビデオの準備ができていません:', {
        width: video.videoWidth,
        height: video.videoHeight,
        readyState: video.readyState
      });
      alert('カメラの準備ができていません。しばらく待ってから再度お試しください。');
    }
  };

  const handleRecognize = async () => {
    if (!selectedFile) {
      alert('画像を選択してください');
      return;
    }

    setIsRecognizing(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post('http://localhost:8000/recognize', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const data = response.data;
      setRecognizedData(data);
      
      // 認識結果をフォームに反映
      setFormData(prev => ({
        ...prev,
        category_large: data.category_large,
        category_medium: data.category_medium,
        name: data.name,
        features: data.features,
        color: data.color,
      }));

    } catch (error) {
      console.error('AI認識エラー:', error);
      alert('AI認識に失敗しました');
    } finally {
      setIsRecognizing(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      // 1. まずテキスト情報のみ登録
      const itemData = { ...formData, image_url: '' };
      const res = await axios.post('http://localhost:8000/items', itemData);
      const item = res.data;
      // 2. 画像ファイルがあればアップロード
      if (selectedFile) {
        const formDataImg = new FormData();
        formDataImg.append('file', selectedFile);
        await axios.post(`http://localhost:8000/items/${item.item_id}/image`, formDataImg, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      }
      alert('拾得物の登録が完了しました');
      navigate('/menu');
    } catch (error) {
      console.error('登録エラー:', error);
      alert('登録に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: keyof ItemForm, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
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
            
            <h2 className="text-2xl font-bold text-gray-800 mb-6">新規拾得物登録</h2>
            
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* 画像アップロードセクション */}
              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">画像アップロード（任意）</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  {/* ファイル選択 */}
                  <div className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 transition-colors">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="flex flex-col items-center space-y-2 text-blue-600 hover:text-blue-700"
                    >
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <span className="text-sm font-medium">既存の写真を選択</span>
                    </button>
                  </div>

                  {/* カメラ撮影 */}
                  <div className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 transition-colors">
                    <button
                      type="button"
                      onClick={isCameraActive ? stopCamera : startCamera}
                      className="flex flex-col items-center space-y-2 text-green-600 hover:text-green-700"
                    >
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span className="text-sm font-medium">
                        {isCameraActive ? 'カメラ停止' : 'カメラで撮影'}
                      </span>
                    </button>
                  </div>

                  {/* 画像なしで登録 */}
                  <div className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 transition-colors">
                    <div className="flex flex-col items-center space-y-2 text-gray-600">
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-sm font-medium">テキストのみで登録</span>
                    </div>
                  </div>
                </div>

                {/* カメラビュー */}
                {isCameraActive && (
                  <div className="mb-4">
                    <div className="relative w-full max-w-md mx-auto">
                      <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        muted
                        className="w-full border rounded-lg"
                        style={{ transform: 'scaleX(-1)' }} // ミラー表示
                      />
                      <canvas ref={canvasRef} className="hidden" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="border-2 border-white border-dashed rounded-lg p-4">
                          <div className="text-white text-center">
                            <div className="text-sm">撮影エリア</div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="text-center mt-2 text-sm text-gray-600">
                      {stream ? 'カメラが起動しました。撮影ボタンを押して写真を撮影してください。' : 'カメラを起動中...'}
                    </div>
                    <div className="flex justify-center mt-4 space-x-4">
                      <button
                        type="button"
                        onClick={capturePhoto}
                        className="px-6 py-3 bg-red-600 text-white rounded-full hover:bg-red-700 font-medium shadow-lg"
                      >
                        📸 写真を撮影
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          console.log('カメラ状態テスト');
                          if (videoRef.current) {
                            const video = videoRef.current;
                            console.log('ビデオ要素状態:', {
                              srcObject: !!video.srcObject,
                              videoWidth: video.videoWidth,
                              videoHeight: video.videoHeight,
                              readyState: video.readyState,
                              paused: video.paused,
                              ended: video.ended,
                              currentTime: video.currentTime
                            });
                          }
                          if (stream) {
                            console.log('ストリーム状態:', {
                              active: stream.active,
                              tracks: stream.getTracks().map(track => ({
                                kind: track.kind,
                                enabled: track.enabled,
                                readyState: track.readyState
                              }))
                            });
                          }
                        }}
                        className="px-4 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium text-sm"
                      >
                        状態確認
                      </button>
                      <button
                        type="button"
                        onClick={stopCamera}
                        className="px-6 py-3 bg-gray-600 text-white rounded-md hover:bg-gray-700 font-medium"
                      >
                        キャンセル
                      </button>
                    </div>
                    <div className="text-center mt-2 text-sm text-gray-600">
                      カメラが起動しました。撮影ボタンを押して写真を撮影してください。
                    </div>
                    <div className="text-center mt-1 text-xs text-blue-600">
                      ビデオサイズ: {videoRef.current?.videoWidth || 0} x {videoRef.current?.videoHeight || 0}
                    </div>
                  </div>
                )}

                {/* AI認識ボタン */}
                {selectedFile && (
                  <div className="flex justify-center">
                    <button
                      type="button"
                      onClick={handleRecognize}
                      disabled={isRecognizing}
                      className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 font-medium"
                    >
                      {isRecognizing ? 'AI認識中...' : 'AI認識を実行'}
                    </button>
                  </div>
                )}
                
                {/* プレビュー */}
                {previewUrl && (
                  <div className="mt-4 flex justify-center">
                    <div className="relative">
                      <img
                        src={previewUrl}
                        alt="プレビュー"
                        className="max-w-xs max-h-48 object-contain border rounded-lg"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedFile(null);
                          setPreviewUrl('');
                          setImageSource('none');
                        }}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                )}

                {/* 画像なしの場合のメッセージ */}
                {!previewUrl && !isCameraActive && (
                  <div className="text-center text-gray-500 py-8">
                    <svg className="w-16 h-16 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p>画像を選択するか、カメラで撮影してください</p>
                    <p className="text-sm">（画像なしでも登録可能です）</p>
                  </div>
                )}
              </div>

              {/* AI認識結果 */}
              {recognizedData && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <h4 className="font-semibold text-green-800 mb-2">AI認識結果</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>大分類: {recognizedData.category_large}</div>
                    <div>中分類: {recognizedData.category_medium}</div>
                    <div>品名: {recognizedData.name}</div>
                    <div>色: {recognizedData.color}</div>
                    <div className="col-span-2">特徴: {recognizedData.features}</div>
                    <div>信頼度: {(recognizedData.confidence * 100).toFixed(1)}%</div>
                  </div>
                </div>
              )}

              {/* 基本情報セクション */}
              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">基本情報</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      拾得日時 *
                    </label>
                    <input
                      type="datetime-local"
                      value={formData.found_datetime}
                      onChange={(e) => handleInputChange('found_datetime', e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      受付日時 *
                    </label>
                    <input
                      type="datetime-local"
                      value={formData.accepted_datetime}
                      onChange={(e) => handleInputChange('accepted_datetime', e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      拾得場所 *
                    </label>
                    <input
                      type="text"
                      value={formData.found_place}
                      onChange={(e) => handleInputChange('found_place', e.target.value)}
                      required
                      placeholder="例: 1階ロビー"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      拾得者種別
                    </label>
                    <select
                      value={formData.finder_type}
                      onChange={(e) => handleInputChange('finder_type', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="一般">一般</option>
                      <option value="職員">職員</option>
                      <option value="清掃業者">清掃業者</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* 品物情報セクション */}
              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">品物情報</h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      大分類 *
                    </label>
                    <select
                      value={formData.category_large}
                      onChange={e => {
                        handleInputChange('category_large', e.target.value);
                        // 大分類が変わったら中分類もリセット
                        handleInputChange('category_medium', '');
                      }}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">選択してください</option>
                      {largeCategoryOptions.map((cat: string) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      中分類 *
                    </label>
                    <select
                      value={formData.category_medium}
                      onChange={e => handleInputChange('category_medium', e.target.value)}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={!formData.category_large}
                    >
                      <option value="">選択してください</option>
                      {mediumCategoryOptions.map((cat: string) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      品名 *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => handleInputChange('name', e.target.value)}
                      required
                      placeholder="例: ハンドバッグ"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      色 *
                    </label>
                    <input
                      type="text"
                      value={formData.color}
                      onChange={(e) => handleInputChange('color', e.target.value)}
                      required
                      placeholder="例: 黒"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      特徴・詳細 *
                    </label>
                    <textarea
                      value={formData.features}
                      onChange={(e) => handleInputChange('features', e.target.value)}
                      required
                      rows={3}
                      placeholder="例: 革製、ブランドロゴあり、サイズ約30cm"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              {/* 所有権・報酬セクション */}
              <div className="bg-gray-50 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">所有権・報酬</h3>
                
                <div className="space-y-4">
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="claims_ownership"
                      checked={formData.claims_ownership}
                      onChange={(e) => handleInputChange('claims_ownership', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="claims_ownership" className="ml-2 block text-sm text-gray-700">
                      拾得者が所有権を主張
                    </label>
                  </div>
                  
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      id="claims_reward"
                      checked={formData.claims_reward}
                      onChange={(e) => handleInputChange('claims_reward', e.target.checked)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                    <label htmlFor="claims_reward" className="ml-2 block text-sm text-gray-700">
                      拾得者が報酬を要求
                    </label>
                  </div>
                </div>
              </div>

              {/* 送信ボタン */}
              <div className="flex justify-end space-x-4">
                <button
                  type="button"
                  onClick={() => navigate('/menu')}
                  className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {isSubmitting ? '登録中...' : '登録する'}
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>
    </div>
  );
};

export default RegisterScreen; 