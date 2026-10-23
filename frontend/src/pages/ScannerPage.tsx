import React, { useState, useRef, useEffect } from 'react';
import {
  Camera,
  QrCode,
  Scan,
  ShoppingCart,
  CheckCircle2,
  AlertCircle,
  Plus,
  Minus,
  Trash2,
  DollarSign,
  ArrowRight,
  RefreshCw,
  Upload,
  Sparkles,
  Printer,
  ShieldCheck,
  Zap,
  Package,
  Layers,
  Clock
} from 'lucide-react';
import { api } from '../services/api';
import { SessionStateStrip } from '../components/overview/SessionStateStrip';
import type { Product, CVScanResult, PaymentQrResponse, PaymentReceipt, CartItem } from '../types';

interface ScannerPageProps {
  onNavigate?: (route: string) => void;
}

export const ScannerPage: React.FC<ScannerPageProps> = ({ onNavigate }) => {
  // Camera & Vision state
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<CVScanResult | null>(null);
  const [activeBarcode, setActiveBarcode] = useState('');

  // POS Cart State
  const [cart, setCart] = useState<CartItem[]>([]);
  const [quickSaleMsg, setQuickSaleMsg] = useState<string | null>(null);

  // Payment State
  const [paymentQr, setPaymentQr] = useState<PaymentQrResponse | null>(null);
  const [isGeneratingQr, setIsGeneratingQr] = useState(false);
  const [isVerifyingPayment, setIsVerifyingPayment] = useState(false);
  const [paymentReceipt, setPaymentReceipt] = useState<PaymentReceipt | null>(null);
  const [customUtr, setCustomUtr] = useState('');
  const [paymentTab, setPaymentTab] = useState<'qr' | 'scanner'>('qr');

  // Automated Flow & State Machine Countdown
  const [sessionState, setSessionState] = useState<string>('IDLE');
  const [autoNavCountdown, setAutoNavCountdown] = useState<number | null>(null);
  const autoNavTimerRef = useRef<number | null>(null);

  // Dynamic quick product selection fetched from real catalog
  const [quickProducts, setQuickProducts] = useState<Product[]>([]);

  useEffect(() => {
    api.getProducts({ per_page: 6 }).then(res => {
      if (res && res.items && res.items.length > 0) {
        setQuickProducts(res.items);
      }
    }).catch(() => {});
  }, []);

  // Initialize and Stop Camera
  const startCamera = async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
        setCameraActive(true);
      }
    } catch (err: any) {
      setCameraError('Camera access denied or unavailable. You can use image upload or click Quick Demo Presets below.');
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Run CV recognition on captured frame or image
  const captureAndRecognize = async (overrideBase64?: string, labelHint?: string, barcodeHint?: string) => {
    setIsScanning(true);
    setScanResult(null);

    let base64Image = overrideBase64;

    if (!base64Image && videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        base64Image = canvas.toDataURL('image/jpeg', 0.85);
      }
    }

    try {
      const res = await api.recognizeProduct({
        image_data: base64Image,
        barcode: barcodeHint || activeBarcode || undefined,
        label: labelHint
      });
      setScanResult(res);
    } catch (err: any) {
      alert(err?.message || 'CV Recognition failed');
    } finally {
      setIsScanning(false);
    }
  };

  // Upload Photo for analysis
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      captureAndRecognize(base64);
    };
    reader.readAsDataURL(file);
  };

  // Add Detected Product to POS Cart
  const addToCart = (product: Product) => {
    setCart(prev => {
      const existing = prev.find(item => item.product_id === product.id);
      if (existing) {
        return prev.map(item =>
          item.product_id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [
        ...prev,
        {
          product_id: product.id,
          sku: product.sku,
          name: product.name,
          category: product.category,
          price: product.selling_price,
          quantity: 1,
          current_stock: product.current_stock
        }
      ];
    });
  };

  const updateCartQuantity = (productId: number, delta: number) => {
    setCart(prev =>
      prev
        .map(item => {
          if (item.product_id === productId) {
            const nextQty = item.quantity + delta;
            return nextQty > 0 ? { ...item, quantity: nextQty } : null;
          }
          return item;
        })
        .filter(Boolean) as CartItem[]
    );
  };

  const removeFromCart = (productId: number) => {
    setCart(prev => prev.filter(item => item.product_id !== productId));
  };

  // 1-Click Quick Sale (Single Unit)
  const handleQuickSale = async (productId: number) => {
    try {
      const res = await api.quickSale({ product_id: productId, quantity: 1 });
      setQuickSaleMsg(res.message);
      setTimeout(() => setQuickSaleMsg(null), 4000);
      // Update local product stock
      if (scanResult?.product && scanResult.product.id === productId) {
        setScanResult({
          ...scanResult,
          product: { ...scanResult.product, current_stock: res.new_stock }
        });
      }
    } catch (err: any) {
      alert(err?.message || 'Quick sale failed');
    }
  };

  // Calculate Cart Totals
  const subtotal = cart.reduce((sum, it) => sum + it.price * it.quantity, 0);
  const gstTax = Math.round(subtotal * 0.05 * 100) / 100; // 5% retail GST
  const grandTotal = Math.round((subtotal + gstTax) * 100) / 100;

  // Generate UPI Payment QR
  const handleGeneratePaymentQr = async () => {
    if (grandTotal <= 0) return;
    setIsGeneratingQr(true);
    setPaymentReceipt(null);
    try {
      const res = await api.generatePaymentQr({
        amount: grandTotal,
        purpose: 'pos_checkout'
      });
      setPaymentQr(res);
    } catch (err: any) {
      alert(err?.message || 'Failed to generate UPI QR');
    } finally {
      setIsGeneratingQr(false);
    }
  };

  const triggerAutoNav = () => {
    setAutoNavCountdown(2);
  };

  useEffect(() => {
    if (autoNavCountdown === null) return;
    if (autoNavCountdown <= 0) {
      setAutoNavCountdown(null);
      if (onNavigate) {
        onNavigate('record');
      }
      return;
    }
    const timer = window.setTimeout(() => {
      setAutoNavCountdown(prev => (prev !== null ? prev - 1 : null));
    }, 1000);
    return () => clearTimeout(timer);
  }, [autoNavCountdown, onNavigate]);

  // Poll backend session state machine as single source of truth
  useEffect(() => {
    const pollSession = async () => {
      try {
        const state = await api.getSessionState();
        setSessionState(state.state);
        if (state.state === 'PAID' && autoNavCountdown === null && !paymentReceipt) {
          triggerAutoNav();
        }
      } catch (e) {
        // quiet poll
      }
    };

    const interval = setInterval(pollSession, 2500);
    return () => clearInterval(interval);
  }, [autoNavCountdown, paymentReceipt]);

  // Verify and Settle Payment
  const handleSettlePayment = async () => {
    if (!paymentQr) return;
    setIsVerifyingPayment(true);
    try {
      const res = await api.verifyPayment({
        transaction_ref: paymentQr.transaction_ref,
        amount: paymentQr.amount,
        payment_method: 'UPI_QR',
        utr_number: customUtr || undefined,
        cart_items: cart
      });
      setPaymentReceipt(res);
      setCart([]); // Clear cart upon successful settlement
      triggerAutoNav();
    } catch (err: any) {
      alert(err?.message || 'Payment verification failed');
    } finally {
      setIsVerifyingPayment(false);
    }
  };

  // Test Gateway Signed Webhook Callback (Demo Mode)
  const handleSimulateWebhook = async () => {
    if (!paymentQr) return;
    setIsVerifyingPayment(true);
    try {
      const res = await api.simulateWebhookPayment({
        transaction_ref: paymentQr.transaction_ref,
        amount: paymentQr.amount,
        cart_items: cart,
        utr_number: customUtr || `UTR-WH-${Date.now().toString().slice(-6)}`
      });
      setPaymentReceipt(res);
      setCart([]);
      triggerAutoNav();
    } catch (err: any) {
      alert(err?.message || 'Webhook simulation failed');
    } finally {
      setIsVerifyingPayment(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#172B4D] tracking-tight flex items-center gap-2">
            <Scan className="w-7 h-7 text-blue-600" />
            Smart Vision Scanner & UPI POS Terminal
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time Computer Vision product recognition, instant optical barcode identification, and Dynamic UPI checkout.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <ShieldCheck className="w-3.5 h-3.5" />
            CV Vision Engine Online
          </span>
        </div>
      </div>

      {/* Session State Strip & CV Model Status Overview */}
      <SessionStateStrip
        currentState={sessionState}
        modelStatus="ACTIVE"
        measuredFps={15.0}
      />

      {/* Quick Sale Feedback Toast */}
      {quickSaleMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs font-semibold flex items-center justify-between animate-fade-in shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            {quickSaleMsg}
          </div>
          <button onClick={() => setQuickSaleMsg(null)} className="text-emerald-700 hover:text-emerald-900">
            &times;
          </button>
        </div>
      )}

      {/* Two Column Grid: Scanner & Viewfinder on Left, POS Cart & Payment on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: Computer Vision Scanner (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Camera className="w-4 h-4 text-blue-600" />
                Live Camera & Optical Viewfinder
              </h2>
              <div className="flex items-center gap-2">
                {cameraActive ? (
                  <button
                    onClick={stopCamera}
                    className="px-3 py-1 text-xs font-semibold text-rose-600 bg-rose-50 border border-rose-200 rounded-lg hover:bg-rose-100 transition-colors"
                  >
                    Stop Camera
                  </button>
                ) : (
                  <button
                    onClick={startCamera}
                    className="px-3 py-1 text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-1.5"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    Open Camera
                  </button>
                )}
              </div>
            </div>

            {/* Viewfinder Window */}
            <div className="relative aspect-video bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center border-2 border-slate-700">
              {/* Hidden canvas for pixel extraction */}
              <canvas ref={canvasRef} className="hidden" />

              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
              />

              {!cameraActive && (
                <div className="text-center p-6 space-y-3">
                  <div className="w-14 h-14 mx-auto rounded-full bg-slate-800 text-slate-400 flex items-center justify-center">
                    <Scan className="w-7 h-7" />
                  </div>
                  <div className="text-slate-300 text-xs font-medium">
                    Webcam feed is inactive. Start camera or upload a product photo.
                  </div>
                  <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer shadow-xs">
                    <Upload className="w-3.5 h-3.5" />
                    Upload Product Image
                    <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
                  </label>
                </div>
              )}

              {/* Optical Crosshair Overlay */}
              {cameraActive && (
                <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
                  <div className="w-48 h-48 border-2 border-blue-400/80 rounded-2xl relative animate-pulse">
                    <div className="absolute top-0 left-0 w-4 h-4 border-t-4 border-l-4 border-blue-500 -mt-1 -ml-1 rounded-tl" />
                    <div className="absolute top-0 right-0 w-4 h-4 border-t-4 border-r-4 border-blue-500 -mt-1 -mr-1 rounded-tr" />
                    <div className="absolute bottom-0 left-0 w-4 h-4 border-b-4 border-l-4 border-blue-500 -mb-1 -ml-1 rounded-bl" />
                    <div className="absolute bottom-0 right-0 w-4 h-4 border-b-4 border-r-4 border-blue-500 -mb-1 -mr-1 rounded-br" />
                    {/* Laser scan line animation */}
                    <div className="w-full h-0.5 bg-blue-400/90 shadow-[0_0_8px_#3b82f6] absolute top-1/2 -translate-y-1/2 animate-bounce" />
                  </div>
                  <span className="text-[11px] font-mono text-white/80 bg-slate-900/60 px-2 py-0.5 rounded mt-3 backdrop-blur-xs">
                    Align Product or Barcode in Crosshair
                  </span>
                </div>
              )}
            </div>

            {/* Scan Action Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Or enter barcode / SKU..."
                  value={activeBarcode}
                  onChange={e => setActiveBarcode(e.target.value)}
                  className="px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg uppercase w-44"
                />
                <button
                  onClick={() => captureAndRecognize(undefined, undefined, activeBarcode)}
                  disabled={isScanning}
                  className="px-3 py-1.5 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900 transition-colors disabled:opacity-50"
                >
                  Lookup
                </button>
              </div>

              {cameraActive && (
                <button
                  onClick={() => captureAndRecognize()}
                  disabled={isScanning}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin' : ''}`} />
                  <span>{isScanning ? 'Analyzing with CV...' : 'Capture & Identify Product'}</span>
                </button>
              )}
            </div>

            {/* Demo Presets Palette for Instant Hackathon Demonstration */}
            <div className="pt-3 border-t border-slate-100">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-2">
                Active Store Catalog Quick Select (From API):
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {quickProducts.map((p) => (
                  <button
                    key={p.sku}
                    onClick={() => captureAndRecognize(undefined, p.name, p.sku)}
                    className="p-2 rounded-lg border border-slate-200 text-left hover:border-blue-500 hover:bg-blue-50/40 transition-colors text-xs"
                  >
                    <div className="font-semibold text-slate-900 truncate">{p.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between mt-0.5">
                      <span>{p.sku}</span>
                      <span className="font-bold text-slate-700">₹{p.selling_price.toFixed(2)}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Detected Product Card */}
          {scanResult && scanResult.product && (
            <div className="bg-white rounded-xl border border-blue-200 p-5 shadow-xs animate-scale-in space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                      {scanResult.product.sku}
                    </span>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                      <Sparkles className="w-3 h-3" />
                      {scanResult.confidence_percentage} Confidence
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {scanResult.recognition_mode}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mt-1">{scanResult.product.name}</h3>
                  <p className="text-xs text-slate-500">{scanResult.product.category}</p>
                </div>

                <div className="text-right">
                  <div className="text-2xl font-extrabold text-slate-900 font-mono">
                    ₹{scanResult.product.selling_price.toFixed(2)}
                  </div>
                  <div className="text-xs text-slate-400">Unit Retail Price</div>
                </div>
              </div>

              {/* Inventory Status Bar */}
              <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                <div>
                  <span className="text-slate-500 block">Current On-Hand</span>
                  <span className={`font-bold font-mono text-sm ${scanResult.product.current_stock < 10 ? 'text-red-600' : 'text-slate-900'}`}>
                    {scanResult.product.current_stock} units
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Perishable Window</span>
                  <span className="font-semibold text-slate-800">
                    {scanResult.product.is_perishable ? `${scanResult.product.shelf_life_days}d Shelf Life` : 'Non-perishable'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Supplier Pack</span>
                  <span className="font-semibold text-slate-800">
                    {scanResult.product.pack_size} units/box
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2.5 pt-1">
                <button
                  onClick={() => addToCart(scanResult.product!)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
                >
                  <ShoppingCart className="w-3.5 h-3.5" />
                  Add to POS Cart
                </button>
                <button
                  onClick={() => handleQuickSale(scanResult.product!.id)}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors"
                >
                  <Zap className="w-3.5 h-3.5" />
                  Quick Sell (1 Unit)
                </button>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: POS Billing Cart & Payment Terminal (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-blue-600" />
                Retail POS Billing Basket ({cart.length})
              </h2>
              {cart.length > 0 && (
                <button
                  onClick={() => setCart([])}
                  className="text-xs text-rose-600 hover:text-rose-700 font-medium"
                >
                  Clear All
                </button>
              )}
            </div>

            {/* Cart Items List */}
            {cart.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <ShoppingCart className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                <p className="text-xs font-medium text-slate-600">POS Cart is Empty</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Scan items or click demo presets to populate checkout.
                </p>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1 divide-y divide-slate-100">
                {cart.map((item) => (
                  <div key={item.product_id} className="pt-2.5 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-slate-900">{item.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {item.sku} • ₹{item.price.toFixed(2)} each
                      </div>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <div className="flex items-center border border-slate-200 rounded-lg">
                        <button
                          onClick={() => updateCartQuantity(item.product_id, -1)}
                          className="p-1 hover:bg-slate-100 text-slate-600"
                        >
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="px-2 font-mono font-bold text-slate-900">{item.quantity}</span>
                        <button
                          onClick={() => updateCartQuantity(item.product_id, 1)}
                          className="p-1 hover:bg-slate-100 text-slate-600"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      <span className="font-mono font-bold text-slate-900 w-16 text-right">
                        ₹{(item.price * item.quantity).toFixed(2)}
                      </span>
                      <button
                        onClick={() => removeFromCart(item.product_id)}
                        className="text-slate-400 hover:text-rose-600"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Bill Summary Breakdown */}
            {cart.length > 0 && (
              <div className="pt-3 border-t border-slate-200 space-y-1.5 text-xs">
                <div className="flex justify-between text-slate-600">
                  <span>Subtotal:</span>
                  <span className="font-mono">₹{subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>GST (5% Tax):</span>
                  <span className="font-mono">₹{gstTax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-base font-bold text-slate-900 pt-1.5 border-t border-slate-100">
                  <span>Total Amount:</span>
                  <span className="font-mono text-blue-700">₹{grandTotal.toFixed(2)}</span>
                </div>

                <button
                  onClick={handleGeneratePaymentQr}
                  disabled={isGeneratingQr}
                  className="w-full mt-3 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  <QrCode className="w-4 h-4" />
                  <span>{isGeneratingQr ? 'Generating UPI Code...' : `Generate UPI Payment QR (₹${grandTotal.toFixed(2)})`}</span>
                </button>
              </div>
            )}
          </div>

          {/* DYNAMIC UPI PAYMENT MODAL / TERMINAL */}
          {paymentQr && (
            <div className="bg-white rounded-xl border-2 border-emerald-500/80 p-5 shadow-lg space-y-4 animate-scale-in">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold text-xs">
                    UPI
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">Dynamic Payment Gateway</h3>
                    <p className="text-[10px] text-slate-500 font-mono">Ref: {paymentQr.transaction_ref}</p>
                  </div>
                </div>
                <button onClick={() => setPaymentQr(null)} className="text-slate-400 hover:text-slate-600 font-bold">
                  &times;
                </button>
              </div>

              {/* Rendered Scannable SVG QR Code */}
              <div className="text-center p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div
                  className="inline-block p-2 bg-white rounded-xl shadow-xs"
                  dangerouslySetInnerHTML={{ __html: paymentQr.qr_svg }}
                />
                <div className="mt-2 text-xl font-extrabold text-slate-900 font-mono">
                  ₹{paymentQr.amount.toFixed(2)}
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Scan with GPay, PhonePe, Paytm, or BHIM UPI
                </p>
                <div className="mt-1 text-[10px] font-mono text-slate-400 bg-white px-2 py-0.5 rounded inline-block border border-slate-200">
                  VPA: {paymentQr.vpa}
                </div>
              </div>

              {/* Payment Verification / Scanner Controls */}
              <div className="space-y-2">
                <label className="block text-[11px] font-semibold text-slate-700">
                  Scan Customer Transaction Screen or Enter UTR (Optional):
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. 328492049281"
                    value={customUtr}
                    onChange={e => setCustomUtr(e.target.value)}
                    className="flex-1 px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg"
                  />
                  <button
                    onClick={handleSettlePayment}
                    disabled={isVerifyingPayment}
                    className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{isVerifyingPayment ? 'Verifying...' : 'Confirm Paid'}</span>
                  </button>
                </div>

                {/* Gateway Signed Webhook Simulation (Demo Mode) */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">Demo Testing:</span>
                  <button
                    onClick={handleSimulateWebhook}
                    disabled={isVerifyingPayment}
                    className="px-2.5 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 rounded-lg transition-colors flex items-center gap-1"
                  >
                    <Zap className="w-3 h-3 text-blue-600" />
                    Simulate Signed Gateway Webhook
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* PAYMENT SETTLEMENT RECEIPT */}
          {paymentReceipt && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 shadow-xs space-y-3 animate-fade-in">
              <div className="flex items-center justify-between text-emerald-900">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <span className="font-bold text-sm">Payment Verified & Settled!</span>
                </div>
                <span className="text-xs font-mono text-emerald-700 font-bold">PAID</span>
              </div>

              <div className="bg-white p-3 rounded-lg border border-emerald-200/80 text-xs space-y-1 font-mono">
                <div className="flex justify-between">
                  <span className="text-slate-500">Ref:</span>
                  <span className="font-bold">{paymentReceipt.transaction_ref}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Bank UTR:</span>
                  <span>{paymentReceipt.utr_number}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Amount Paid:</span>
                  <span className="text-emerald-700 font-bold text-sm">₹{paymentReceipt.amount_settled.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Timestamp:</span>
                  <span>{paymentReceipt.timestamp}</span>
                </div>
              </div>

              <p className="text-[11px] text-emerald-800">
                ✓ Inventory stock levels decremented automatically.<br />
                ✓ Transaction logged into sales ledger & audit trail.
              </p>

              <button
                onClick={() => setPaymentReceipt(null)}
                className="w-full py-1.5 bg-white border border-emerald-300 text-emerald-900 rounded-lg text-xs font-semibold hover:bg-emerald-100/50"
              >
                Close & Next Transaction
              </button>
            </div>
          )}

          {/* AUTOMATED FLOW: COUNTDOWN MODAL TO LIVE RECORD */}
          {autoNavCountdown !== null && (
            <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-emerald-200 text-center space-y-4 animate-scale-in">
                <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Payment Settled Successfully!</h3>
                  <p className="text-xs text-slate-600 mt-1">
                    Checkout complete. Automatically launching the <strong className="text-violet-700">Live Record Page</strong> for shelf & traffic object detection in:
                  </p>
                </div>
                <div className="text-4xl font-black text-emerald-600 font-mono">
                  {autoNavCountdown}s
                </div>
                <div className="flex items-center justify-center gap-2 pt-2">
                  <button
                    onClick={() => setAutoNavCountdown(null)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Stay on Scanner
                  </button>
                  <button
                    onClick={() => {
                      setAutoNavCountdown(null);
                      if (onNavigate) onNavigate('record');
                    }}
                    className="px-4 py-2 text-xs font-bold text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm shadow-violet-500/20"
                  >
                    <span>Launch Record Now</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
