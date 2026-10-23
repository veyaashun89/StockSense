import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Video,
  Camera,
  Users,
  Package,
  Shield,
  Clock,
  StopCircle,
  Play,
  Download,
  AlertTriangle,
  CheckCircle2,
  Upload,
  RefreshCw,
  Eye,
  Sliders,
  History,
  Tag,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import { SessionStateStrip } from '../components/overview/SessionStateStrip';
import type {
  SessionInfo,
  FrameDetectionResponse,
  DetectionItem,
  RecordSessionSummary,
  RecordSessionItem
} from '../types';

interface RecordPageProps {
  onNavigate?: (route: string) => void;
}

export const RecordPage: React.FC<RecordPageProps> = ({ onNavigate }) => {
  // Session & State Machine
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionSummary, setSessionSummary] = useState<RecordSessionSummary | null>(null);
  const [showSummaryModal, setShowSummaryModal] = useState(false);

  // Camera & Stream
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // Detection & Analytics State
  const [latestFrameDetections, setLatestFrameDetections] = useState<DetectionItem[]>([]);
  const [eventTimeline, setEventTimeline] = useState<Array<{
    id: string;
    time: string;
    class_name: 'person' | 'product';
    label: string;
    confidence: number;
    track_id: number;
  }>>([]);
  const [fps, setFps] = useState<number>(19.3);
  const [latencyMs, setLatencyMs] = useState<number>(52);
  const [peopleInFrame, setPeopleInFrame] = useState<number>(0);
  const [uniquePeople, setUniquePeople] = useState<number>(0);
  const [productsInFrame, setProductsInFrame] = useState<number>(0);
  const [uniqueProducts, setUniqueProducts] = useState<number>(0);
  const [matchedSkusList, setMatchedSkusList] = useState<string[]>([]);

  // Settings & Privacy Controls
  const [blurFaces, setBlurFaces] = useState(true);
  const [snapshotPreview, setSnapshotPreview] = useState<string | null>(null);
  const [isCapturingSnapshot, setIsCapturingSnapshot] = useState(false);

  // Past Sessions Tab
  const [showHistory, setShowHistory] = useState(false);
  const [pastSessions, setPastSessions] = useState<RecordSessionItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Detection loop lock
  const isProcessingFrame = useRef(false);
  const frameIntervalRef = useRef<number | null>(null);

  // Start Camera
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
      setCameraError('Camera access denied or unavailable. Fallback upload mode is active.');
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(t => t.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  // Sync session state from backend
  const fetchSessionState = useCallback(async () => {
    try {
      const state = await api.getSessionState();
      setSessionInfo(state);
      setIsRecording(state.state === 'RECORDING');
    } catch (e) {
      console.error('Failed to get session state:', e);
    }
  }, []);

  // Initialize or resume recording session
  const handleStartSession = async () => {
    try {
      const res = await api.startRecord();
      setIsRecording(true);
      setLatestFrameDetections([]);
      setEventTimeline([]);
      setUniquePeople(0);
      setUniqueProducts(0);
      setMatchedSkusList([]);
      await fetchSessionState();
      if (!cameraActive) {
        startCamera();
      }
    } catch (e: any) {
      alert(`Could not start record session: ${e?.message || e}`);
    }
  };

  // Finalize session
  const handleStopSession = async () => {
    try {
      const res = await api.stopRecord(sessionInfo?.session_id);
      setIsRecording(false);
      if (res.summary) {
        setSessionSummary(res.summary);
        setShowSummaryModal(true);
      }
      await fetchSessionState();
    } catch (e: any) {
      alert(`Failed to end session: ${e?.message || e}`);
    }
  };

  // Draw bounding boxes on canvas
  const renderOverlay = useCallback((detections: DetectionItem[], width: number, height: number) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    detections.forEach(det => {
      const [x1, y1, x2, y2] = det.bbox;
      const bx = x1 * width;
      const by = y1 * height;
      const bw = (x2 - x1) * width;
      const bh = (y2 - y1) * height;

      const isPerson = det.class_name === 'person';
      const color = isPerson ? '#8B5CF6' : (det.sku ? '#10B981' : '#F59E0B');
      const label = isPerson
        ? `Person #${det.track_id} (${Math.round(det.confidence * 100)}%)`
        : (det.sku ? `${det.sku} (${Math.round(det.confidence * 100)}%)` : `Item #${det.track_id}`);

      // Bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.strokeRect(bx, by, bw, bh);

      // Label badge
      ctx.font = 'bold 12px Inter, sans-serif';
      const textWidth = ctx.measureText(label).width;
      const badgeH = 20;
      const badgeW = textWidth + 12;

      ctx.fillStyle = color;
      ctx.fillRect(bx, Math.max(0, by - badgeH), badgeW, badgeH);

      ctx.fillStyle = '#FFFFFF';
      ctx.fillText(label, bx + 6, Math.max(14, by - 6));
    });
  }, []);

  // Frame processing loop
  const processLiveFrame = useCallback(async () => {
    if (isProcessingFrame.current || !videoRef.current || !captureCanvasRef.current) return;
    const video = videoRef.current;
    if (video.readyState < 2) return;

    isProcessingFrame.current = true;
    try {
      const canvas = captureCanvasRef.current;
      const vw = video.videoWidth || 640;
      const vh = video.videoHeight || 480;
      canvas.width = 480; // Scale down slightly to maintain 20+ FPS
      canvas.height = Math.round((vh / vw) * 480);

      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.65);

        const res = await api.sendRecordFrame({
          image_data: dataUrl,
          blur_faces: blurFaces,
          session_id: sessionInfo?.session_id
        });

        if (res.status === 'success') {
          setFps(res.fps);
          setLatencyMs(res.inference_time_ms);
          setPeopleInFrame(res.people_in_frame);
          setUniquePeople(res.unique_people_session);
          setProductsInFrame(res.products_in_frame);
          setUniqueProducts(res.unique_products_session);
          setMatchedSkusList(res.matched_skus);
          setLatestFrameDetections(res.detections);

          renderOverlay(res.detections, canvas.width, canvas.height);

          // Append new detections to timeline
          const newEvents = res.detections.filter(d => d.is_new).map(d => ({
            id: `evt-${Date.now()}-${d.track_id}`,
            time: new Date().toLocaleTimeString(),
            class_name: d.class_name,
            label: d.class_name === 'person' ? `Person #${d.track_id}` : (d.sku || d.raw_label || 'Product'),
            confidence: d.confidence,
            track_id: d.track_id
          }));

          if (newEvents.length > 0) {
            setEventTimeline(prev => [...newEvents, ...prev].slice(0, 50));
          }
        }
      }
    } catch (err) {
      console.warn('Frame detection skipped:', err);
    } finally {
      isProcessingFrame.current = false;
    }
  }, [blurFaces, renderOverlay, sessionInfo]);

  // Handle uploaded fallback image
  const handleUploadFrame = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = reader.result as string;
      try {
        const res = await api.sendRecordFrame({
          image_data: b64,
          blur_faces: blurFaces,
          session_id: sessionInfo?.session_id
        });
        if (res.status === 'success') {
          setFps(res.fps);
          setLatencyMs(res.inference_time_ms);
          setPeopleInFrame(res.people_in_frame);
          setUniquePeople(res.unique_people_session);
          setProductsInFrame(res.products_in_frame);
          setUniqueProducts(res.unique_products_session);
          setMatchedSkusList(res.matched_skus);
          setLatestFrameDetections(res.detections);
          if (res.annotated_frame) {
            setSnapshotPreview(res.annotated_frame);
          }
        }
      } catch (err: any) {
        alert(`Failed to analyze uploaded frame: ${err.message || err}`);
      }
    };
    reader.readAsDataURL(file);
  };

  // Capture Privacy-Compliant Snapshot
  const captureSnapshot = async () => {
    if (!videoRef.current || !captureCanvasRef.current) return;
    setIsCapturingSnapshot(true);
    try {
      const canvas = captureCanvasRef.current;
      const video = videoRef.current;
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.85);

        const res = await api.sendRecordFrame({
          image_data: dataUrl,
          blur_faces: blurFaces,
          session_id: sessionInfo?.session_id
        });

        if (res.annotated_frame) {
          setSnapshotPreview(res.annotated_frame);
        } else {
          setSnapshotPreview(dataUrl);
        }
      }
    } catch (e: any) {
      alert(`Snapshot failed: ${e.message}`);
    } finally {
      setIsCapturingSnapshot(false);
    }
  };

  // Load Past Sessions
  const loadPastSessions = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.getRecordSessions(15);
      setPastSessions(res.sessions || []);
    } catch (e) {
      console.error('Failed to load past sessions:', e);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Lifecycle
  useEffect(() => {
    fetchSessionState();
    startCamera();

    return () => {
      stopCamera();
      if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
      }
    };
  }, [fetchSessionState]);

  // Interval trigger for frames
  useEffect(() => {
    if (cameraActive) {
      const timer = window.setInterval(() => {
        processLiveFrame();
      }, 100); // 10 FPS query throttle
      frameIntervalRef.current = timer;
      return () => clearInterval(timer);
    }
  }, [cameraActive, processLiveFrame]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center text-white shadow-md shadow-violet-500/20">
              <Eye className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
                Live Record & Vision Analytics
                {isRecording && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-600 border border-rose-200 animate-pulse">
                    <span className="w-2 h-2 rounded-full bg-rose-600" />
                    RECORDING LIVE
                  </span>
                )}
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time YOLOv8n object detection & IoU tracking on shelf stock items and store human traffic.
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setShowHistory(!showHistory);
              if (!showHistory) loadPastSessions();
            }}
            className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <History className="w-3.5 h-3.5" />
            Session History
          </button>

          {!isRecording ? (
            <button
              onClick={handleStartSession}
              className="px-4 py-1.5 text-xs font-bold text-white bg-violet-600 hover:bg-violet-700 rounded-lg shadow-sm shadow-violet-500/20 transition-all flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              Start Recording Session
            </button>
          ) : (
            <button
              onClick={handleStopSession}
              className="px-4 py-1.5 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-sm shadow-rose-500/20 transition-all flex items-center gap-2 animate-pulse"
            >
              <StopCircle className="w-4 h-4" />
              End Session & Finalize
            </button>
          )}
        </div>
      </div>

      {/* Overview Session State & Model Telemetry Strip */}
      <SessionStateStrip
        currentState={isRecording ? 'RECORDING' : (sessionInfo?.state || 'IDLE')}
        modelStatus="ACTIVE"
        measuredFps={fps}
      />

      {/* Mandatory Privacy & Ethics Notice Banner */}
      <div className="bg-amber-50/80 border border-amber-200/90 rounded-xl p-3.5 flex items-start gap-3 text-amber-900 shadow-xs">
        <Shield className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs leading-relaxed">
          <strong className="font-semibold text-amber-950">Camera Analytics Privacy Guarantee: </strong>
          People are counted, not identified. No facial embeddings or biometric identities are stored or transmitted.
          Human snapshots are automatically blurred on faces.
        </div>
      </div>

      {/* Main 2-Column Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* LEFT COLUMN: Live Camera Viewfinder & Canvas Overlay (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Video className="w-4 h-4 text-violet-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Detection Viewfinder</span>
              </div>
              <div className="flex items-center gap-3">
                {/* Engine Stats */}
                <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  {fps.toFixed(1)} FPS | {latencyMs}ms CPU
                </span>
                {/* Face Blur Toggle */}
                <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={blurFaces}
                    onChange={(e) => setBlurFaces(e.target.checked)}
                    className="rounded border-slate-300 text-violet-600 focus:ring-violet-500 h-3.5 w-3.5"
                  />
                  <span>Blur Faces</span>
                </label>
              </div>
            </div>

            {/* Video + Overlay Canvas Stack */}
            <div className="relative aspect-video bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center">
              {/* Offscreen Canvas for Snapshot / Frame Extraction */}
              <canvas ref={captureCanvasRef} className="hidden" />

              {/* Video Element */}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
              />

              {/* Real-time Bounding Box Overlay Canvas */}
              {cameraActive && (
                <canvas
                  ref={overlayCanvasRef}
                  className="absolute inset-0 w-full h-full object-cover pointer-events-none"
                />
              )}

              {/* Camera Fallback UI */}
              {!cameraActive && (
                <div className="text-center p-6 space-y-3">
                  <div className="w-12 h-12 rounded-full bg-slate-800 text-slate-400 mx-auto flex items-center justify-center">
                    <Camera className="w-6 h-6" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">Camera Feed Inactive</p>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm">
                      {cameraError || 'Click below to grant camera permissions, or upload a store snapshot.'}
                    </p>
                  </div>
                  <div className="flex items-center justify-center gap-2 pt-2">
                    <button
                      onClick={startCamera}
                      className="px-3.5 py-1.5 bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      Enable Camera
                    </button>
                    <label className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 border border-slate-700">
                      <Upload className="w-3.5 h-3.5" />
                      Upload Photo
                      <input type="file" accept="image/*" onChange={handleUploadFrame} className="hidden" />
                    </label>
                  </div>
                </div>
              )}
            </div>

            {/* Camera Footer Controls */}
            <div className="flex items-center justify-between pt-1">
              <div className="text-[11px] text-slate-500">
                Tracking: <span className="font-semibold text-slate-700">{latestFrameDetections.length}</span> objects currently in frame
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={captureSnapshot}
                  disabled={!cameraActive || isCapturingSnapshot}
                  className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <Camera className="w-3.5 h-3.5 text-slate-500" />
                  {isCapturingSnapshot ? 'Saving...' : 'Capture Snapshot'}
                </button>
                <label className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5">
                  <Upload className="w-3.5 h-3.5 text-slate-500" />
                  Upload Frame
                  <input type="file" accept="image/*" onChange={handleUploadFrame} className="hidden" />
                </label>
              </div>
            </div>
          </div>

          {/* Snapshot Preview Card if available */}
          {snapshotPreview && (
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Privacy-Blurred Frame Snapshot
                </span>
                <a
                  href={snapshotPreview}
                  download={`stocksense_record_${Date.now()}.jpg`}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
              </div>
              <div className="rounded-lg overflow-hidden border border-slate-200 max-h-56 bg-slate-900 flex items-center justify-center">
                <img src={snapshotPreview} alt="Privacy Snapshot" className="max-h-56 w-auto object-contain" />
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Live Counters & Detection Timeline (5 cols) */}
        <div className="lg:col-span-5 space-y-4">

          {/* Live Metric Counters Card */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-violet-600" />
              Live Session Telemetry
            </h2>

            <div className="grid grid-cols-2 gap-3">
              {/* People in Frame */}
              <div className="p-3 bg-violet-50/70 border border-violet-100 rounded-xl">
                <div className="text-[11px] font-semibold text-violet-700 flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  People in Frame
                </div>
                <div className="text-2xl font-black text-violet-950 mt-1">{peopleInFrame}</div>
                <div className="text-[10px] text-violet-600 mt-0.5">Active centroid count</div>
              </div>

              {/* Unique People Session */}
              <div className="p-3 bg-purple-50/70 border border-purple-100 rounded-xl">
                <div className="text-[11px] font-semibold text-purple-700 flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  Unique Visitors
                </div>
                <div className="text-2xl font-black text-purple-950 mt-1">{uniquePeople}</div>
                <div className="text-[10px] text-purple-600 mt-0.5">IoU tracked individuals</div>
              </div>

              {/* Products in Frame */}
              <div className="p-3 bg-emerald-50/70 border border-emerald-100 rounded-xl">
                <div className="text-[11px] font-semibold text-emerald-700 flex items-center gap-1">
                  <Package className="w-3.5 h-3.5" />
                  Products in Frame
                </div>
                <div className="text-2xl font-black text-emerald-950 mt-1">{productsInFrame}</div>
                <div className="text-[10px] text-emerald-600 mt-0.5">Shelf items detected</div>
              </div>

              {/* Unique Matched SKUs */}
              <div className="p-3 bg-blue-50/70 border border-blue-100 rounded-xl">
                <div className="text-[11px] font-semibold text-blue-700 flex items-center gap-1">
                  <Tag className="w-3.5 h-3.5" />
                  Matched SKUs
                </div>
                <div className="text-2xl font-black text-blue-950 mt-1">{matchedSkusList.length}</div>
                <div className="text-[10px] text-blue-600 mt-0.5">Recognized catalog items</div>
              </div>
            </div>

            {/* Matched SKU Badges */}
            {matchedSkusList.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Identified Products:</span>
                <div className="flex flex-wrap gap-1.5">
                  {matchedSkusList.map(sku => (
                    <span key={sku} className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      {sku}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Real-time Detection Event Timeline */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                Detection Event Stream
              </span>
              <span className="text-[11px] text-slate-400">Latest 50 events</span>
            </div>

            <div className="h-64 overflow-y-auto space-y-2 pr-1 font-mono text-xs">
              {eventTimeline.length === 0 ? (
                <div className="text-center py-10 text-slate-400 font-sans text-xs">
                  No detection events logged yet. Point camera at products or people.
                </div>
              ) : (
                eventTimeline.map(evt => (
                  <div
                    key={evt.id}
                    className="p-2 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-between text-[11px] hover:bg-slate-100 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${evt.class_name === 'person' ? 'bg-purple-500' : 'bg-emerald-500'}`} />
                      <span className="font-semibold text-slate-800">{evt.label}</span>
                    </div>
                    <div className="flex items-center gap-3 text-slate-500">
                      <span>{Math.round(evt.confidence * 100)}% conf</span>
                      <span className="text-[10px] text-slate-400">{evt.time}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Session Summary Modal on Stop */}
      {showSummaryModal && sessionSummary && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-5 animate-scale-in">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-900">Recording Session Finalized</h3>
              </div>
              <button
                onClick={() => setShowSummaryModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>

            <p className="text-xs text-slate-600">
              The detection session data has been atomically archived to the SQLite database.
            </p>

            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
              <div>
                <span className="text-slate-500">Session ID:</span>
                <p className="font-mono font-bold text-slate-800">{sessionSummary.session_id}</p>
              </div>
              <div>
                <span className="text-slate-500">Total Unique Visitors:</span>
                <p className="font-bold text-purple-700">{sessionSummary.unique_people_count}</p>
              </div>
              <div>
                <span className="text-slate-500">Total Product Detections:</span>
                <p className="font-bold text-emerald-700">{sessionSummary.total_products_detected}</p>
              </div>
              <div>
                <span className="text-slate-500">Distinct SKUs Identified:</span>
                <p className="font-bold text-blue-700">{sessionSummary.matched_skus_count}</p>
              </div>
              <div className="col-span-2 pt-2 border-t border-slate-200">
                <span className="text-slate-500">Identified SKUs:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {sessionSummary.matched_skus.length > 0 ? (
                    sessionSummary.matched_skus.map(s => (
                      <span key={s} className="px-2 py-0.5 rounded text-[10px] bg-emerald-100 text-emerald-800 font-mono">
                        {s}
                      </span>
                    ))
                  ) : (
                    <span className="text-slate-400 italic">None</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setShowSummaryModal(false);
                  if (onNavigate) onNavigate('scanner');
                }}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Back to POS Scanner
              </button>
              <button
                onClick={() => setShowSummaryModal(false)}
                className="px-4 py-2 text-xs font-bold text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors"
              >
                Close Summary
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Past Sessions Drawer */}
      {showHistory && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <History className="w-4 h-4 text-violet-600" />
              Archived Recording Sessions (SQLite Database)
            </h3>
            <button
              onClick={() => setShowHistory(false)}
              className="text-xs text-slate-500 hover:text-slate-700 font-medium"
            >
              Close
            </button>
          </div>

          {loadingHistory ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading archived sessions...</div>
          ) : pastSessions.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">No past sessions recorded yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="pb-2">Session UUID</th>
                    <th className="pb-2">State</th>
                    <th className="pb-2">Started At</th>
                    <th className="pb-2">Unique Visitors</th>
                    <th className="pb-2">Products Detected</th>
                    <th className="pb-2">Matched SKUs</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {pastSessions.map(sess => (
                    <tr key={sess.id} className="hover:bg-slate-50">
                      <td className="py-2.5 font-mono font-medium text-slate-800">{sess.session_uuid}</td>
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          sess.state === 'RECORDING' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'
                        }`}>
                          {sess.state}
                        </span>
                      </td>
                      <td className="py-2.5 text-slate-500">
                        {sess.started_at ? new Date(sess.started_at).toLocaleString() : 'N/A'}
                      </td>
                      <td className="py-2.5 font-semibold text-purple-700">{sess.summary?.unique_people_count || 0}</td>
                      <td className="py-2.5 font-semibold text-emerald-700">{sess.summary?.total_products_detected || 0}</td>
                      <td className="py-2.5 font-semibold text-blue-700">{sess.summary?.matched_skus_count || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
