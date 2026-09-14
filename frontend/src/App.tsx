import {
  Activity,
  AppWindow,
  ArrowLeft,
  BatteryCharging,
  Bell,
  Boxes,
  Camera,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Database,
  FileText,
  Home,
  Link,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  MonitorCog,
  Pencil,
  Play,
  Plus,
  Power,
  QrCode as QrCodeIcon,
  Radio,
  RefreshCw,
  RotateCcw,
  Server,
  Settings2,
  ShieldCheck,
  SkipBack,
  SkipForward,
  SlidersHorizontal,
  Smartphone,
  Square,
  Sun,
  TerminalSquare,
  Trash2,
  Volume1,
  Volume2,
  VolumeX,
  Wifi,
  X,
} from "lucide-react";
import QRCode from "qrcode";
import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, api, apiBlob, getAdminToken, setAdminToken } from "./api";
import type {
  AuditLog,
  Dashboard,
  Device,
  DeviceDiagnostics,
  Environment,
  ServiceInfo,
  SystemInfo,
  View,
} from "./types";

const navigation = [
  ["dashboard", Activity, "Dashboard"],
  ["devices", Smartphone, "Devices"],
  ["android", SlidersHorizontal, "Android console"],
  ["environments", Boxes, "Environments"],
  ["services", MonitorCog, "Services"],
  ["terminal", TerminalSquare, "Terminal"],
  ["logs", FileText, "Logs"],
  ["settings", Settings2, "Settings"],
] as const;
const statusLabels = {
  CONNECTED: "Connected",
  DISCONNECTED: "Disconnected",
  CONNECTING: "Connecting",
  RECONNECTING: "Reconnecting",
  ERROR: "Connection error",
};
const environmentLabels = { RUNNING: "Running", STOPPED: "Stopped", ERROR: "Error", UNKNOWN: "Unknown" };
const emptyDeviceForm = { name: "", host: "", port: "5555" };
const emptyPairForm = { host: "", port: "", pairing_code: "" };
const emptyEnvironmentForm = { device_id: "", name: "", profile: "default", default_user: "root" };

function relativeTime(value: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return new Date(value).toLocaleDateString();
}

export function App() {
  const [view, setView] = useState<View>("dashboard");
  const [devices, setDevices] = useState<Device[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [selectedEnvironmentId, setSelectedEnvironmentId] = useState("");
  const [modal, setModal] = useState<"device" | "pair" | "environment" | null>(null);
  const [editing, setEditing] = useState<Device | null>(null);
  const [deviceForm, setDeviceForm] = useState(emptyDeviceForm);
  const [pairForm, setPairForm] = useState(emptyPairForm);
  const [environmentForm, setEnvironmentForm] = useState(emptyEnvironmentForm);
  const [terminalCommand, setTerminalCommand] = useState("");
  const [terminalUser, setTerminalUser] = useState("root");
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [tokenInput, setTokenInput] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedEnvironment = environments.find((item) => item.id === selectedEnvironmentId) ?? null;
  const connectedRootedDevices = useMemo(
    () => devices.filter((device) => device.connection_status === "CONNECTED" && device.root_available),
    [devices],
  );

  const bootstrap = async () => {
    try {
      const [loadedDevices, loadedEnvironments, loadedDashboard, loadedLogs, loadedInfo] = await Promise.all([
        api<Device[]>("/api/devices"),
        api<Environment[]>("/api/environments"),
        api<Dashboard>("/api/system/dashboard"),
        api<AuditLog[]>("/api/system/logs"),
        api<SystemInfo>("/api/system/info"),
      ]);
      setDevices(loadedDevices);
      setEnvironments(loadedEnvironments);
      setDashboard(loadedDashboard);
      setLogs(loadedLogs);
      setSystemInfo(loadedInfo);
      setSelectedDeviceId(
        (current) => current || loadedDevices.find((device) => device.connection_status === "CONNECTED")?.id || "",
      );
      setSelectedEnvironmentId((current) => current || loadedEnvironments[0]?.id || "");
      setLocked(false);
      setReady(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setAdminToken("");
        setLocked(true);
        setAuthError("The saved administrator token is no longer valid.");
        setReady(true);
        return;
      }
      setNotice(error instanceof Error ? error.message : "Could not load the control plane.");
      setReady(true);
    }
  };

  useEffect(() => {
    void bootstrap();
  }, []);

  const refreshMeta = async () => {
    const [nextDashboard, nextLogs] = await Promise.all([
      api<Dashboard>("/api/system/dashboard"),
      api<AuditLog[]>("/api/system/logs"),
    ]);
    setDashboard(nextDashboard);
    setLogs(nextLogs);
  };

  const login = async (event: FormEvent) => {
    event.preventDefault();
    setAdminToken(tokenInput.trim());
    setBusy("login");
    try {
      await api<SystemInfo>("/api/system/info");
      setAuthError(null);
      await bootstrap();
      setTokenInput("");
    } catch (error) {
      setAdminToken("");
      setLocked(true);
      setAuthError(error instanceof Error ? error.message : "The administrator token was not accepted.");
    } finally {
      setBusy(null);
    }
  };

  const logout = () => {
    setAdminToken("");
    setLocked(true);
  };

  const openCreateDevice = () => {
    setEditing(null);
    setDeviceForm(emptyDeviceForm);
    setModal("device");
  };

  const openEditDevice = (device: Device) => {
    setEditing(device);
    setDeviceForm({ name: device.name, host: device.host, port: String(device.port) });
    setModal("device");
  };

  const saveDevice = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("save-device");
    try {
      const saved = await api<Device>(editing ? `/api/devices/${editing.id}` : "/api/devices", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...deviceForm, port: Number(deviceForm.port) }),
      });
      setDevices((current) =>
        editing ? current.map((item) => (item.id === saved.id ? saved : item)) : [saved, ...current],
      );
      setModal(null);
      setNotice(editing ? "Device settings saved." : "Device added. Connect it when Android is online.");
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save the device.");
    } finally {
      setBusy(null);
    }
  };

  const pairDevice = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("pair");
    try {
      const response = await api<{ message: string }>("/api/devices/pair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pairForm, port: Number(pairForm.port) }),
      });
      setPairForm(emptyPairForm);
      setModal(null);
      setNotice(response.message);
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Wireless pairing failed.");
    } finally {
      setBusy(null);
    }
  };

  const deviceAction = async (device: Device, operation: "connect" | "disconnect" | "refresh" | "reboot") => {
    setBusy(`${operation}-${device.id}`);
    try {
      const payload = await api<Device | { device: Device; message: string }>(
        `/api/devices/${device.id}/${operation}`,
        { method: "POST" },
      );
      const updated = "device" in payload ? payload.device : payload;
      setDevices((current) => current.map((item) => (item.id === device.id ? updated : item)));
      setNotice("message" in payload ? payload.message : "Device details refreshed.");
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Device operation failed.");
    } finally {
      setBusy(null);
    }
  };

  const removeDevice = async (device: Device) => {
    if (!window.confirm(`Remove ${device.name} and its registered environments?`)) return;
    setBusy(`delete-${device.id}`);
    try {
      await api<null>(`/api/devices/${device.id}`, { method: "DELETE" });
      setDevices((current) => current.filter((item) => item.id !== device.id));
      setEnvironments((current) => current.filter((item) => item.device_id !== device.id));
      setNotice("Device removed.");
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not remove the device.");
    } finally {
      setBusy(null);
    }
  };

  const openCreateEnvironment = () => {
    setEnvironmentForm({ ...emptyEnvironmentForm, device_id: connectedRootedDevices[0]?.id ?? "" });
    setModal("environment");
  };

  const createEnvironment = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("create-environment");
    try {
      const created = await api<Environment>("/api/environments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(environmentForm),
      });
      setEnvironments((current) => [created, ...current]);
      setSelectedEnvironmentId(created.id);
      setModal(null);
      setNotice("Linux Deploy environment registered.");
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not register the environment.");
    } finally {
      setBusy(null);
    }
  };

  const environmentAction = async (environment: Environment, operation: "start" | "stop" | "refresh") => {
    setBusy(`${operation}-${environment.id}`);
    try {
      const payload = await api<Environment | { environment: Environment; output: string }>(
        `/api/environments/${environment.id}/${operation}`,
        { method: "POST" },
      );
      const updated = "environment" in payload ? payload.environment : payload;
      setEnvironments((current) => current.map((item) => (item.id === environment.id ? updated : item)));
      setNotice(operation === "refresh" ? "Environment status refreshed." : `Environment ${operation} completed.`);
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Environment operation failed.");
    } finally {
      setBusy(null);
    }
  };

  const removeEnvironment = async (environment: Environment) => {
    if (!window.confirm(`Remove ${environment.name} from the registry? This does not delete its chroot.`)) return;
    setBusy(`delete-environment-${environment.id}`);
    try {
      await api<null>(`/api/environments/${environment.id}`, { method: "DELETE" });
      setEnvironments((current) => current.filter((item) => item.id !== environment.id));
      if (selectedEnvironmentId === environment.id) setSelectedEnvironmentId("");
      setNotice("Environment removed from the registry. The chroot was not deleted.");
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not remove the environment.");
    } finally {
      setBusy(null);
    }
  };

  const loadServices = async () => {
    if (!selectedEnvironment) return;
    setBusy("load-services");
    try {
      const response = await api<{ services: ServiceInfo[] }>(`/api/environments/${selectedEnvironment.id}/services`);
      setServices(response.services);
      setNotice(response.services.length ? "Service state refreshed." : "No SysV services were reported by this environment.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not inspect services.");
    } finally {
      setBusy(null);
    }
  };

  const controlService = async (name: string, action: "start" | "stop" | "restart" | "status") => {
    if (!selectedEnvironment) return;
    setBusy(`service-${name}`);
    try {
      await api<{ output: string }>(`/api/environments/${selectedEnvironment.id}/services`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, action }),
      });
      await loadServices();
      await refreshMeta();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Service operation failed.");
      setBusy(null);
    }
  };

  const runTerminal = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedEnvironment || !terminalCommand.trim()) return;
    const command = terminalCommand.trim();
    setTerminalCommand("");
    setTerminalOutput((current) => [...current, `$ ${command}`]);
    setBusy("terminal");
    try {
      const response = await api<{ output: string }>(`/api/environments/${selectedEnvironment.id}/terminal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, user: terminalUser }),
      });
      setTerminalOutput((current) => [...current, response.output || "(command completed without output)"]);
      await refreshMeta();
    } catch (error) {
      setTerminalOutput((current) => [...current, `error: ${error instanceof Error ? error.message : "command failed"}`]);
    } finally {
      setBusy(null);
    }
  };

  if (!ready) return <LoadingScreen />;
  if (locked) return <LoginScreen token={tokenInput} busy={busy === "login"} error={authError} onChange={setTokenInput} onSubmit={login} />;

  return (
    <main className="shell">
      <aside className="sidebar">
        <button className="brand" type="button" onClick={() => setView("dashboard")}>
          <span className="brand-mark">A</span><span>Android<br />Server Manager</span>
        </button>
        <nav aria-label="Primary navigation">
          {navigation.map(([id, Icon, label]) => (
            <button className={view === id ? "nav-item active" : "nav-item"} type="button" key={id} onClick={() => setView(id)}>
              <Icon size={18} />{label}
            </button>
          ))}
        </nav>
        <div className="node-state"><i />Wi-Fi control plane ready</div>
      </aside>

      <section className="workspace">
        <Topbar view={view} devices={devices} onAddDevice={openCreateDevice} onAddEnvironment={openCreateEnvironment} />
        {notice && <Notice message={notice} onClose={() => setNotice(null)} />}
        <div className="rule" />
        {view === "dashboard" && <DashboardView dashboard={dashboard} devices={devices} environments={environments} onNavigate={setView} />}
        {view === "devices" && <DevicesView devices={devices} busy={busy} onAdd={openCreateDevice} onPair={() => setModal("pair")} onEdit={openEditDevice} onRemove={removeDevice} onAction={deviceAction} />}
        {view === "android" && <AndroidConsoleView devices={devices} selectedId={selectedDeviceId} onSelect={setSelectedDeviceId} onNotice={setNotice} />}
        {view === "environments" && <EnvironmentsView environments={environments} devices={devices} canAdd={connectedRootedDevices.length > 0} busy={busy} onAdd={openCreateEnvironment} onAction={environmentAction} onRemove={removeEnvironment} />}
        {view === "services" && <ServicesView environments={environments} selectedId={selectedEnvironmentId} services={services} busy={busy} onSelect={setSelectedEnvironmentId} onLoad={loadServices} onControl={controlService} />}
        {view === "terminal" && <TerminalView environments={environments} selectedId={selectedEnvironmentId} user={terminalUser} command={terminalCommand} output={terminalOutput} busy={busy === "terminal"} onSelect={setSelectedEnvironmentId} onUser={setTerminalUser} onCommand={setTerminalCommand} onSubmit={runTerminal} onClear={() => setTerminalOutput([])} />}
        {view === "logs" && <LogsView logs={logs} devices={devices} onRefresh={() => void refreshMeta()} />}
        {view === "settings" && <SettingsView info={systemInfo} tokenPresent={Boolean(getAdminToken())} onLogout={logout} />}
      </section>

      {modal === "device" && <DeviceModal editing={editing} form={deviceForm} busy={busy === "save-device"} onChange={setDeviceForm} onClose={() => setModal(null)} onSubmit={saveDevice} />}
      {modal === "pair" && <PairModal form={pairForm} busy={busy === "pair"} onChange={setPairForm} onClose={() => setModal(null)} onSubmit={pairDevice} onNotice={setNotice} />}
      {modal === "environment" && <EnvironmentModal devices={connectedRootedDevices} form={environmentForm} busy={busy === "create-environment"} onChange={setEnvironmentForm} onClose={() => setModal(null)} onSubmit={createEnvironment} />}
    </main>
  );
}

function LoadingScreen() {
  return <main className="gate"><LoaderCircle className="spin" size={28} /><p>Starting control plane…</p></main>;
}

function LoginScreen({ token, busy, error, onChange, onSubmit }: { token: string; busy: boolean; error: string | null; onChange: (value: string) => void; onSubmit: (event: FormEvent) => void }) {
  return <main className="gate"><section className="login-panel"><span className="login-mark"><LockKeyhole size={24} /></span><p className="kicker">Protected control plane</p><h1>Administrator access</h1><p>Enter the token configured on your ZimaOS server. It stays in this browser tab only.</p>{error && <p className="login-error" role="alert">{error}</p>}<form onSubmit={onSubmit}><label>Admin token<input autoFocus required type="password" value={token} onChange={(event) => onChange(event.target.value)} /></label><button className="primary-action" disabled={busy} type="submit">{busy && <LoaderCircle className="spin" size={15} />}Unlock</button></form></section></main>;
}

function Topbar({ view, devices, onAddDevice, onAddEnvironment }: { view: View; devices: Device[]; onAddDevice: () => void; onAddEnvironment: () => void }) {
  const titles: Record<View, [string, string]> = {
    dashboard: ["Fleet overview", "See what needs attention across Android and Linux Deploy."],
    devices: ["Android devices", "Manage trusted ADB endpoints on your private Wi-Fi."],
    android: ["Android console", "Operate Android directly with safe ADB controls and a non-root shell."],
    environments: ["Linux environments", "Control registered Linux Deploy profiles on rooted nodes."],
    services: ["Service control", "Inspect and operate SysV services inside a running chroot."],
    terminal: ["Environment terminal", "Run an intentional command inside a selected Linux Deploy profile."],
    logs: ["Activity log", "Review control-plane actions and failures in chronological order."],
    settings: ["Runtime settings", "Verify security, ADB, persistence, and Linux Deploy configuration."],
  };
  return <header><div><p className="kicker">{view === "dashboard" ? "Control plane" : "Workspace"}</p><h1>{titles[view][0]}</h1><p className="lede">{titles[view][1]}</p></div><div className="header-actions">{view === "devices" && <button className="primary-action" type="button" onClick={onAddDevice}><Plus size={17} />Add device</button>}{view === "environments" && <button className="primary-action" type="button" onClick={onAddEnvironment} disabled={!devices.some((device) => device.connection_status === "CONNECTED" && device.root_available)}><Plus size={17} />Add environment</button>}</div></header>;
}

function Notice({ message, onClose }: { message: string; onClose: () => void }) {
  return <div className="notice" role="status">{message}<button type="button" aria-label="Dismiss message" onClick={onClose}><X size={16} /></button></div>;
}

function DashboardView({ dashboard, devices, environments, onNavigate }: { dashboard: Dashboard | null; devices: Device[]; environments: Environment[]; onNavigate: (view: View) => void }) {
  return <div className="dashboard-layout"><section className="fleet-signal"><div><span className="signal-count">{dashboard?.connected_devices ?? 0}</span><span className="signal-total">/{dashboard?.total_devices ?? 0} nodes online</span></div><p>{dashboard?.devices_with_errors ? `${dashboard.devices_with_errors} device needs attention.` : "No connection errors reported."}</p><div className="signal-track"><span style={{ width: `${dashboard?.total_devices ? (dashboard.connected_devices / dashboard.total_devices) * 100 : 0}%` }} /></div></section><section className="metric-strip"><div><span>Root ready</span><strong>{dashboard?.rooted_devices ?? 0}</strong></div><div><span>Environments</span><strong>{environments.length}</strong></div><div><span>Running</span><strong>{environments.filter((item) => item.status === "RUNNING").length}</strong></div></section><section className="topology-panel"><div className="section-heading"><div><h2>Compute chain</h2><p>Each environment is anchored to one Wi-Fi node.</p></div><button className="text-action" onClick={() => onNavigate("devices")}>Manage devices</button></div>{devices.length ? <div className="topology-list">{devices.map((device) => <div className="topology-row" key={device.id}><span className={`topology-node ${device.connection_status === "CONNECTED" ? "online" : ""}`}><Smartphone size={18} /></span><div><strong>{device.name}</strong><small>{device.host}:{device.port}</small></div><span className="topology-line" /><div><strong>{environments.filter((item) => item.device_id === device.id).length} environments</strong><small>{device.root_available ? "Root available" : "Root unavailable"}</small></div></div>)}</div> : <Empty title="No nodes yet" copy="Add your first Android device to establish the compute chain." action="Add a device" onAction={() => onNavigate("devices")} />}</section><section className="activity-panel"><div className="section-heading"><div><h2>Recent activity</h2><p>Persisted control-plane events.</p></div><button className="text-action" onClick={() => onNavigate("logs")}>View all logs</button></div><ActivityList logs={dashboard?.recent_activity ?? []} /></section></div>;
}

function DevicesView({ devices, busy, onAdd, onPair, onEdit, onRemove, onAction }: { devices: Device[]; busy: string | null; onAdd: () => void; onPair: () => void; onEdit: (device: Device) => void; onRemove: (device: Device) => void; onAction: (device: Device, action: "connect" | "disconnect" | "refresh" | "reboot") => void }) {
  if (!devices.length) return <Empty title="No Android nodes enrolled" copy="Use classic ADB on port 5555, or pair Android 11 and newer with a wireless debugging code." action="Add first device" onAction={onAdd} secondary="Pair wirelessly" onSecondary={onPair} />;
  return <><div className="page-tools"><button className="secondary-action" type="button" onClick={onPair}><Radio size={16} />Pair wirelessly</button></div><section className="device-grid">{devices.map((device) => <article className="device-card" key={device.id}><div className="card-top"><div className="device-name"><span className="phone-icon"><Smartphone size={20} /></span><div><h2>{device.name}</h2><p>{device.manufacturer && device.model ? `${device.manufacturer} ${device.model}` : "Awaiting inspection"}</p></div></div><span className={`status ${device.connection_status.toLowerCase()}`}><i />{statusLabels[device.connection_status]}</span></div><div className="device-specs"><span><Wifi size={15} />{device.host}:{device.port}</span><span><ShieldCheck size={15} />{device.root_available === null ? "Root not checked" : device.root_available ? "Root available" : "Root unavailable"}</span>{device.android_version && <span>Android {device.android_version} · {device.cpu_abi}</span>}{device.kernel && <span>Kernel {device.kernel}</span>}</div>{device.last_error && <p className="device-error">{device.last_error}</p>}<div className="card-actions">{device.connection_status === "CONNECTED" ? <><ActionButton onClick={() => onAction(device, "refresh")} disabled={busy !== null} icon={<RefreshCw size={15} />} label="Refresh" /><ActionButton onClick={() => onAction(device, "reboot")} disabled={busy !== null} icon={<Power size={15} />} label="Reboot" /><ActionButton onClick={() => onAction(device, "disconnect")} disabled={busy !== null} label="Disconnect" /></> : <button className="connect-button" type="button" onClick={() => onAction(device, "connect")} disabled={busy !== null}>{busy === `connect-${device.id}` ? <LoaderCircle size={15} className="spin" /> : <Wifi size={15} />}Connect via Wi-Fi</button>}</div><div className="card-management"><button onClick={() => onEdit(device)}><Pencil size={14} />Edit</button><button className="danger-subtle" onClick={() => onRemove(device)}><Trash2 size={14} />Remove</button></div></article>)}</section></>;
}

type AndroidAction =
  | "home"
  | "back"
  | "recent"
  | "lock"
  | "wake"
  | "volume_up"
  | "volume_down"
  | "mute"
  | "media_play_pause"
  | "media_next"
  | "media_previous"
  | "notifications"
  | "quick_settings"
  | "open_settings";

const androidActions: { id: AndroidAction; label: string; icon: ReactNode }[] = [
  { id: "home", label: "Home", icon: <Home size={17} /> },
  { id: "back", label: "Back", icon: <ArrowLeft size={17} /> },
  { id: "recent", label: "Recent", icon: <AppWindow size={17} /> },
  { id: "wake", label: "Wake", icon: <Sun size={17} /> },
  { id: "lock", label: "Lock", icon: <LockKeyhole size={17} /> },
  { id: "volume_up", label: "Volume +", icon: <Volume2 size={17} /> },
  { id: "volume_down", label: "Volume −", icon: <Volume1 size={17} /> },
  { id: "mute", label: "Mute", icon: <VolumeX size={17} /> },
  { id: "media_previous", label: "Previous", icon: <SkipBack size={17} /> },
  { id: "media_play_pause", label: "Play / pause", icon: <Play size={17} /> },
  { id: "media_next", label: "Next", icon: <SkipForward size={17} /> },
  { id: "notifications", label: "Notifications", icon: <Bell size={17} /> },
  { id: "quick_settings", label: "Quick settings", icon: <SlidersHorizontal size={17} /> },
  { id: "open_settings", label: "Settings", icon: <Settings2 size={17} /> },
];

const termuxPresets = [
  ["Battery JSON", "termux-battery-status"],
  ["Location", "termux-location"],
  ["Wi-Fi info", "termux-wifi-connectioninfo"],
  ["Sensors", "termux-sensor -l"],
  ["Clipboard", "termux-clipboard-get"],
  ["Torch on", "termux-torch on"],
] as const;

function formatUptime(seconds: number | null) {
  if (seconds === null) return "Unknown";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days ? `${days}d ` : ""}${hours}h ${minutes}m`;
}

function AndroidConsoleView({
  devices,
  selectedId,
  onSelect,
  onNotice,
}: {
  devices: Device[];
  selectedId: string;
  onSelect: (id: string) => void;
  onNotice: (message: string) => void;
}) {
  const connected = devices.filter((device) => device.connection_status === "CONNECTED");
  const selected = connected.find((device) => device.id === selectedId) ?? null;
  const [diagnostics, setDiagnostics] = useState<DeviceDiagnostics | null>(null);
  const [packages, setPackages] = useState<string[]>([]);
  const [packageName, setPackageName] = useState("");
  const [command, setCommand] = useState("");
  const [root, setRoot] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const [termuxCommand, setTermuxCommand] = useState("");
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadConsole = useCallback(async () => {
    if (!selected) {
      setDiagnostics(null);
      setPackages([]);
      return;
    }
    setBusy("refresh");
    try {
      const [nextDiagnostics, nextPackages] = await Promise.all([
        api<DeviceDiagnostics>(`/api/devices/${selected.id}/diagnostics`),
        api<{ packages: string[] }>(`/api/devices/${selected.id}/apps`),
      ]);
      setDiagnostics(nextDiagnostics);
      setPackages(nextPackages.packages);
      setPackageName((current) => nextPackages.packages.includes(current) ? current : nextPackages.packages[0] || "");
    } catch (error) {
      setDiagnostics(null);
      setPackages([]);
      onNotice(error instanceof Error ? error.message : "Could not inspect Android.");
    } finally {
      setBusy(null);
    }
  }, [onNotice, selected]);

  useEffect(() => {
    void loadConsole();
  }, [loadConsole]);

  useEffect(() => {
    if (selected?.root_available !== true) setRoot(false);
  }, [selected]);

  useEffect(() => {
    return () => {
      if (screenshotUrl) URL.revokeObjectURL(screenshotUrl);
    };
  }, [screenshotUrl]);

  const sendAction = async (action: AndroidAction) => {
    if (!selected) return;
    setBusy(`action-${action}`);
    try {
      const response = await api<{ message: string }>(`/api/devices/${selected.id}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      onNotice(response.message);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Android rejected the action.");
    } finally {
      setBusy(null);
    }
  };

  const runShell = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected || !command.trim()) return;
    const nextCommand = command.trim();
    setCommand("");
    setOutput((current) => [...current, `${root ? "root" : "shell"}@${selected.name}: $ ${nextCommand}`]);
    setBusy("shell");
    try {
      const response = await api<{ output: string; root: boolean }>(`/api/devices/${selected.id}/shell`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: nextCommand, root }),
      });
      setOutput((current) => [...current, response.output || "(command completed without output)"]);
    } catch (error) {
      setOutput((current) => [...current, `error: ${error instanceof Error ? error.message : "command failed"}`]);
    } finally {
      setBusy(null);
    }
  };

  const launchPackage = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected || !packageName) return;
    setBusy("launch-app");
    try {
      const response = await api<{ message: string }>(`/api/devices/${selected.id}/apps/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ package: packageName }),
      });
      onNotice(response.message);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not open the Android app.");
    } finally {
      setBusy(null);
    }
  };

  const openTermux = async () => {
    if (!selected) return;
    setBusy("open-termux");
    try {
      const response = await api<{ message: string }>(`/api/devices/${selected.id}/termux/open`, { method: "POST" });
      onNotice(response.message);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not open Termux.");
    } finally {
      setBusy(null);
    }
  };

  const runTermux = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected || !termuxCommand.trim()) return;
    setBusy("termux");
    try {
      const response = await api<{ message: string }>(`/api/devices/${selected.id}/termux/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: termuxCommand.trim() }),
      });
      setTermuxCommand("");
      onNotice(response.message);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not start the Termux command.");
    } finally {
      setBusy(null);
    }
  };

  const captureScreen = async () => {
    if (!selected) return;
    setBusy("screenshot");
    try {
      const image = await apiBlob(`/api/devices/${selected.id}/screenshot`);
      setScreenshotUrl(URL.createObjectURL(image));
      onNotice("Fresh Android screenshot captured.");
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not capture the Android screen.");
    } finally {
      setBusy(null);
    }
  };

  if (!connected.length) {
    return <Empty title="No connected Android device" copy="Connect a trusted Wi-Fi ADB endpoint first. The console never requires a USB cable." />;
  }

  return (
    <div className="android-console">
      <section className="console-context">
        <label className="context-picker">
          Android device
          <select value={selectedId} onChange={(event) => onSelect(event.target.value)}>
            <option value="">Select a connected device</option>
            {connected.map((device) => <option value={device.id} key={device.id}>{device.name} · {device.host}</option>)}
          </select>
        </label>
        <div className="console-context-state">
          <span className="access-chip"><ShieldCheck size={14} />ADB shell available</span>
          <span className={`access-chip ${selected?.root_available ? "root" : "muted"}`}>
            {selected?.root_available ? "Root available" : "Non-root device"}
          </span>
          <button className="secondary-action" disabled={!selected || busy !== null} onClick={() => void loadConsole()}>
            <RefreshCw className={busy === "refresh" ? "spin" : ""} size={15} />Refresh telemetry
          </button>
        </div>
      </section>

      {!selected ? <Empty title="Choose a connected device" copy="All controls run through that device's authorized ADB-over-Wi-Fi session." /> : <>
        <section className="telemetry-strip">
          <div className="telemetry-primary">
            <BatteryCharging size={20} />
            <span><strong>{diagnostics?.battery_level ?? "—"}%</strong><small>{diagnostics?.battery_status ?? "Battery unavailable"}{diagnostics?.temperature_c !== null && diagnostics?.temperature_c !== undefined ? ` · ${diagnostics.temperature_c}°C` : ""}</small></span>
          </div>
          <div><Wifi size={17} /><span><strong>{diagnostics?.wifi_ipv4 ?? "Not detected"}</strong><small>Wi-Fi address</small></span></div>
          <div><Radio size={17} /><span><strong>{diagnostics?.tailscale_ipv4 ?? "Not detected"}</strong><small>Tailscale address</small></span></div>
          <div><Clock3 size={17} /><span><strong>{formatUptime(diagnostics?.uptime_seconds ?? null)}</strong><small>Android uptime</small></span></div>
          <div><Smartphone size={17} /><span><strong>{diagnostics?.screen_state ?? "Unknown"}</strong><small>Screen state</small></span></div>
        </section>

        <div className="console-grid">
          <section className="control-bench">
            <div className="bench-heading"><div><p className="kicker">Remote keys</p><h2>Android controls</h2></div><small>No root required</small></div>
            <div className="action-pad">
              {androidActions.map((action) => (
                <button key={action.id} disabled={busy !== null} type="button" onClick={() => void sendAction(action.id)}>
                  {action.icon}<span>{action.label}</span>
                </button>
              ))}
            </div>

            <div className="bench-divider" />
            <div className="bench-heading"><div><p className="kicker">Launcher</p><h2>Installed apps</h2></div><small>{packages.length} user apps</small></div>
            <form className="package-launcher" onSubmit={launchPackage}>
              <select value={packageName} onChange={(event) => setPackageName(event.target.value)}>
                {!packages.length && <option value="">No user apps reported</option>}
                {packages.map((item) => <option value={item} key={item}>{item}</option>)}
              </select>
              <button disabled={!packageName || busy !== null} type="submit"><Play size={14} />Open</button>
            </form>

            <div className="bench-divider" />
            <div className="bench-heading"><div><p className="kicker">Termux bridge</p><h2>Phone automations</h2></div><span className={`service-light ${diagnostics?.termux_installed ? "on" : "off"}`} /></div>
            <p className="bench-copy">Opening Termux works without root. Starting commands inside Termux from ADB requires root because Termux rejects intents sent by Android's shell user.</p>
            <button className="secondary-action bench-button" disabled={!diagnostics?.termux_installed || busy !== null} type="button" onClick={() => void openTermux()}>
              <TerminalSquare size={15} />Open Termux
            </button>
            <form className="termux-form" onSubmit={runTermux}>
              <input value={termuxCommand} onChange={(event) => setTermuxCommand(event.target.value)} placeholder="termux-battery-status" />
              <button disabled={!selected.root_available || !diagnostics?.termux_installed || !termuxCommand.trim() || busy !== null} type="submit">Start session</button>
            </form>
            <div className="termux-presets" aria-label="Termux API command examples">
              {termuxPresets.map(([label, preset]) => <button key={preset} type="button" onClick={() => setTermuxCommand(preset)}>{label}</button>)}
            </div>
            {!selected.root_available && <p className="capability-note"><LockKeyhole size={13} />Termux command bridge locked on this non-root phone. Use the ADB shell beside it.</p>}
          </section>

          <section className="adb-shell-panel">
            <div className="shell-toolbar">
              <div><p className="kicker">Direct device session</p><h2>ADB shell</h2></div>
              <div className="shell-mode" aria-label="Shell privilege mode">
                <button className={!root ? "active" : ""} type="button" onClick={() => setRoot(false)}>shell</button>
                <button className={root ? "active" : ""} disabled={!selected.root_available} type="button" onClick={() => setRoot(true)}>root</button>
              </div>
            </div>
            <p className="shell-safety"><ShieldCheck size={14} />The default <code>shell</code> mode works on personal phones without root after ADB authorization.</p>
            <div className="device-terminal-output" aria-live="polite">
              {output.length ? output.map((line, index) => <pre key={`${index}-${line.slice(0, 12)}`}>{line}</pre>) : <p>Try <code>getprop ro.build.version.release</code>, <code>df -h /sdcard</code>, or <code>pm list packages -3</code>.</p>}
              {busy === "shell" && <span className="terminal-cursor" />}
            </div>
            <form className="terminal-form device-terminal-form" onSubmit={runShell}>
              <span>$</span>
              <input value={command} disabled={busy === "shell"} placeholder="Enter an Android shell command" onChange={(event) => setCommand(event.target.value)} />
              <button disabled={!command.trim() || busy === "shell"} type="submit">Run</button>
            </form>
          </section>

          <section className="screen-panel">
            <div className="bench-heading"><div><p className="kicker">Visual check</p><h2>Device screen</h2></div><span>{diagnostics?.screen_state ?? "Unknown"}</span></div>
            <div className="screen-canvas">
              {screenshotUrl ? <img src={screenshotUrl} alt={`Current screen of ${selected.name}`} /> : <div><Camera size={28} /><p>Capture a still image from Android.</p></div>}
            </div>
            <button className="secondary-action bench-button" disabled={busy !== null} type="button" onClick={() => void captureScreen()}>
              <Camera size={15} />{busy === "screenshot" ? "Capturing…" : "Capture screen"}
            </button>
            <details className="storage-details"><summary>Android storage report</summary><pre>{diagnostics?.storage || "Storage telemetry unavailable."}</pre></details>
          </section>
        </div>
      </>}
    </div>
  );
}

function EnvironmentsView({ environments, devices, canAdd, busy, onAdd, onAction, onRemove }: { environments: Environment[]; devices: Device[]; canAdd: boolean; busy: string | null; onAdd: () => void; onAction: (environment: Environment, action: "start" | "stop" | "refresh") => void; onRemove: (environment: Environment) => void }) {
  if (!environments.length) return <Empty title="No Linux Deploy profiles registered" copy={canAdd ? "Register a profile that already exists in Linux Deploy on a connected Android node." : "Connect a rooted Android device before registering its Linux Deploy profile."} action="Add environment" onAction={onAdd} disabled={!canAdd} />;
  return <section className="table-panel"><div className="table-head"><span>Environment</span><span>Android node</span><span>Profile</span><span>Status</span><span>Actions</span></div>{environments.map((environment) => { const device = devices.find((item) => item.id === environment.device_id); return <div className="table-row" key={environment.id}><div><strong>{environment.name}</strong><small>User: {environment.default_user}</small></div><div><strong>{device?.name ?? "Removed device"}</strong><small>{device ? `${device.host}:${device.port}` : "Unavailable"}</small></div><code>{environment.profile}</code><span className={`environment-status ${environment.status.toLowerCase()}`}>{environmentLabels[environment.status]}</span><div className="row-actions"><button onClick={() => onAction(environment, "refresh")} disabled={busy !== null} aria-label="Refresh environment"><RefreshCw size={14} /></button>{environment.status === "RUNNING" ? <button onClick={() => onAction(environment, "stop")} disabled={busy !== null}><Square size={13} />Stop</button> : <button onClick={() => onAction(environment, "start")} disabled={busy !== null}><Play size={14} />Start</button>}<button className="danger-icon" onClick={() => onRemove(environment)} disabled={busy !== null} aria-label="Remove environment"><Trash2 size={14} /></button></div></div>; })}</section>;
}

function EnvironmentPicker({ environments, value, onChange }: { environments: Environment[]; value: string; onChange: (value: string) => void }) {
  return <label className="context-picker">Environment<select value={value} onChange={(event) => onChange(event.target.value)}><option value="">Select an environment</option>{environments.map((environment) => <option value={environment.id} key={environment.id}>{environment.name} · {environment.profile}</option>)}</select></label>;
}

function ServicesView({ environments, selectedId, services, busy, onSelect, onLoad, onControl }: { environments: Environment[]; selectedId: string; services: ServiceInfo[]; busy: string | null; onSelect: (id: string) => void; onLoad: () => void; onControl: (name: string, action: "start" | "stop" | "restart" | "status") => void }) {
  return <section className="operations-panel"><div className="operation-toolbar"><EnvironmentPicker environments={environments} value={selectedId} onChange={onSelect} /><button className="secondary-action" onClick={onLoad} disabled={!selectedId || busy !== null}><RefreshCw size={15} />Inspect services</button></div>{!selectedId ? <Empty title="Choose an environment" copy="Service commands run inside the selected Linux Deploy chroot." /> : services.length ? <div className="service-list">{services.map((service) => <div className="service-row" key={service.name}><span className={`service-light ${service.running === true ? "on" : service.running === false ? "off" : "unknown"}`} /><div><strong>{service.name}</strong><small>{service.running === true ? "Running" : service.running === false ? "Stopped" : "Status unknown"}</small></div><div className="row-actions"><button onClick={() => onControl(service.name, service.running ? "restart" : "start")} disabled={busy !== null}>{service.running ? <RotateCcw size={14} /> : <Play size={14} />}{service.running ? "Restart" : "Start"}</button>{service.running && <button onClick={() => onControl(service.name, "stop")} disabled={busy !== null}><Square size={13} />Stop</button>}</div></div>)}</div> : <Empty title="Services not inspected" copy="Inspect the environment to read services reported by its SysV service manager." action="Inspect now" onAction={onLoad} />}</section>;
}

function TerminalView({ environments, selectedId, user, command, output, busy, onSelect, onUser, onCommand, onSubmit, onClear }: { environments: Environment[]; selectedId: string; user: string; command: string; output: string[]; busy: boolean; onSelect: (id: string) => void; onUser: (value: string) => void; onCommand: (value: string) => void; onSubmit: (event: FormEvent) => void; onClear: () => void }) {
  return <section className="terminal-panel"><div className="operation-toolbar"><EnvironmentPicker environments={environments} value={selectedId} onChange={onSelect} /><label className="compact-field">User<input value={user} pattern="[A-Za-z0-9._-]+" onChange={(event) => onUser(event.target.value)} /></label><button className="text-action" onClick={onClear}>Clear output</button></div><div className="terminal-output" aria-live="polite">{output.length ? output.map((line, index) => <pre key={`${index}-${line.slice(0, 10)}`}>{line}</pre>) : <p>Select a running environment and enter a command. Commands execute inside its chroot.</p>}{busy && <span className="terminal-cursor" />}</div><form className="terminal-form" onSubmit={onSubmit}><span>$</span><input disabled={!selectedId || busy} value={command} placeholder={selectedId ? "uname -a" : "Select an environment first"} onChange={(event) => onCommand(event.target.value)} /><button disabled={!selectedId || busy || !command.trim()} type="submit">Run</button></form></section>;
}

function LogsView({ logs, devices, onRefresh }: { logs: AuditLog[]; devices: Device[]; onRefresh: () => void }) {
  return <section className="log-panel"><div className="section-heading"><div><h2>Audit trail</h2><p>Up to 100 recent actions are retained in the application database.</p></div><button className="secondary-action" onClick={onRefresh}><RefreshCw size={15} />Refresh</button></div><ActivityList logs={logs} devices={devices} expanded /></section>;
}

function ActivityList({ logs, devices = [], expanded = false }: { logs: AuditLog[]; devices?: Device[]; expanded?: boolean }) {
  if (!logs.length) return <p className="muted-copy">No activity recorded yet.</p>;
  return <div className={`activity-list ${expanded ? "expanded" : ""}`}>{logs.map((entry) => <div className="activity-row" key={entry.id}>{entry.level === "ERROR" ? <CircleAlert className="activity-icon error" size={17} /> : <CheckCircle2 className="activity-icon" size={17} />}<div><strong>{entry.message}</strong><small>{entry.action}{entry.device_id ? ` · ${devices.find((device) => device.id === entry.device_id)?.name ?? entry.device_id.slice(0, 8)}` : ""}</small></div><time dateTime={entry.created_at}>{relativeTime(entry.created_at)}</time></div>)}</div>;
}

function SettingsView({ info, tokenPresent, onLogout }: { info: SystemInfo | null; tokenPresent: boolean; onLogout: () => void }) {
  if (!info) return <Empty title="Settings unavailable" copy="Runtime information could not be loaded." />;
  return <div className="settings-grid"><section className="settings-section"><div className="settings-title"><ShieldCheck size={20} /><div><h2>Access control</h2><p>API requests use a Bearer administrator token.</p></div></div><dl><div><dt>Authentication</dt><dd>{info.authentication_enabled ? "Enabled" : "Disabled"}</dd></div><div><dt>Browser token</dt><dd>{tokenPresent ? "Loaded for this tab" : "Not required"}</dd></div></dl>{tokenPresent && <button className="secondary-action" onClick={onLogout}><LogOut size={15} />Lock session</button>}</section><section className="settings-section"><div className="settings-title"><Wifi size={20} /><div><h2>ADB over Wi-Fi</h2><p>Transport settings supplied by the container environment.</p></div></div><dl><div><dt>Binary</dt><dd><code>{info.adb_path}</code></dd></div><div><dt>Server port</dt><dd>{info.adb_server_port}</dd></div><div><dt>Timeout</dt><dd>{info.adb_timeout}s</dd></div></dl></section><section className="settings-section"><div className="settings-title"><Server size={20} /><div><h2>Linux Deploy</h2><p>CLI invoked through rooted ADB shell.</p></div></div><dl><div><dt>CLI path</dt><dd><code>{info.linux_deploy_cli}</code></dd></div></dl></section><section className="settings-section"><div className="settings-title"><Database size={20} /><div><h2>Application</h2><p>Read-only diagnostics. Change values in `.env` and restart.</p></div></div><dl><div><dt>Version</dt><dd>{info.version}</dd></div><div><dt>Database</dt><dd>{info.database_backend}</dd></div></dl></section></div>;
}

function Empty({ title, copy, action, onAction, secondary, onSecondary, disabled = false }: { title: string; copy: string; action?: string; onAction?: () => void; secondary?: string; onSecondary?: () => void; disabled?: boolean }) {
  return <section className="empty-state"><div className="device-orbit"><Server size={30} /></div><div><h2>{title}</h2><p>{copy}</p>{action && <div className="empty-actions"><button className="primary-action" disabled={disabled} onClick={onAction}>{action}</button>{secondary && <button className="text-action" onClick={onSecondary}><Link size={15} />{secondary}</button>}</div>}</div></section>;
}

function ActionButton({ icon, label, disabled, onClick }: { icon?: ReactNode; label: string; disabled: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} disabled={disabled}>{icon}{label}</button>;
}

type DeviceForm = typeof emptyDeviceForm;
type PairForm = typeof emptyPairForm;
type EnvironmentForm = typeof emptyEnvironmentForm;

function ModalShell({ children, titleId, onClose }: { children: ReactNode; titleId: string; onClose: () => void }) {
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className="device-modal" role="dialog" aria-modal="true" aria-labelledby={titleId}><button className="close-modal" type="button" onClick={onClose} aria-label="Close"><X size={18} /></button>{children}</section></div>;
}

function DeviceModal({ editing, form, busy, onChange, onClose, onSubmit }: { editing: Device | null; form: DeviceForm; busy: boolean; onChange: (form: DeviceForm) => void; onClose: () => void; onSubmit: (event: FormEvent) => void }) {
  return <ModalShell titleId="device-modal-title" onClose={onClose}><p className="kicker">Wi-Fi endpoint</p><h2 id="device-modal-title">{editing ? "Edit Android device" : "Add Android device"}</h2><p className="modal-copy">Use the connection address shown by wireless debugging, or port 5555 for classic ADB over TCP.</p><form onSubmit={onSubmit}><label>Name<input required value={form.name} placeholder="S20+" onChange={(event) => onChange({ ...form, name: event.target.value })} /></label><label>Host<input required value={form.host} placeholder="192.168.1.30" onChange={(event) => onChange({ ...form, host: event.target.value })} /></label><label>ADB connection port<input required type="number" min="1" max="65535" value={form.port} onChange={(event) => onChange({ ...form, port: event.target.value })} /></label><FormActions busy={busy} label={editing ? "Save changes" : "Add device"} onCancel={onClose} /></form></ModalShell>;
}

type QRPairingSession = {
  session_id: string;
  qr_payload: string;
  service_name: string;
  expires_in_seconds: number;
};

function PairModal({
  form,
  busy,
  onChange,
  onClose,
  onSubmit,
  onNotice,
}: {
  form: PairForm;
  busy: boolean;
  onChange: (form: PairForm) => void;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  onNotice: (message: string) => void;
}) {
  const [mode, setMode] = useState<"code" | "qr">("code");
  const [qrSession, setQrSession] = useState<QRPairingSession | null>(null);
  const [qrImage, setQrImage] = useState("");
  const [qrBusy, setQrBusy] = useState(false);

  const generateQr = async () => {
    setQrBusy(true);
    try {
      const session = await api<QRPairingSession>("/api/devices/pair/qr", { method: "POST" });
      const image = await QRCode.toDataURL(session.qr_payload, {
        width: 320,
        margin: 2,
        errorCorrectionLevel: "M",
        color: { dark: "#10181eff", light: "#ffffffff" },
      });
      setQrSession(session);
      setQrImage(image);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "Could not generate the QR pairing session.");
    } finally {
      setQrBusy(false);
    }
  };

  const completeQr = async () => {
    if (!qrSession) return;
    setQrBusy(true);
    try {
      const response = await api<{ message: string }>("/api/devices/pair/qr/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: qrSession.session_id }),
      });
      onClose();
      onNotice(response.message);
    } catch (error) {
      onNotice(error instanceof Error ? error.message : "The phone was not discovered after scanning the QR code.");
    } finally {
      setQrBusy(false);
    }
  };

  return (
    <ModalShell titleId="pair-modal-title" onClose={onClose}>
      <p className="kicker">Android 11 or newer</p>
      <h2 id="pair-modal-title">Pair wireless debugging</h2>
      <div className="pair-tabs" role="tablist" aria-label="Pairing method">
        <button className={mode === "code" ? "active" : ""} type="button" role="tab" aria-selected={mode === "code"} onClick={() => setMode("code")}><Radio size={15} />Six-digit code</button>
        <button className={mode === "qr" ? "active" : ""} type="button" role="tab" aria-selected={mode === "qr"} onClick={() => setMode("qr")}><QrCodeIcon size={15} />QR code</button>
      </div>

      {mode === "code" ? <>
        <p className="modal-copy">Open Wireless debugging → Pair device with pairing code on Android. Enter that temporary address and code here.</p>
        <form onSubmit={onSubmit}>
          <label>Pairing host<input required value={form.host} placeholder="192.168.1.30" onChange={(event) => onChange({ ...form, host: event.target.value })} /></label>
          <label>Pairing port<input required type="number" min="1" max="65535" value={form.port} placeholder="37123" onChange={(event) => onChange({ ...form, port: event.target.value })} /></label>
          <label>Pairing code<input required inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} value={form.pairing_code} placeholder="123456" onChange={(event) => onChange({ ...form, pairing_code: event.target.value })} /></label>
          <p className="form-hint">After pairing, add the device with the separate connection port shown on the Wireless debugging screen.</p>
          <FormActions busy={busy} label="Pair device" onCancel={onClose} />
        </form>
      </> : <section className="qr-pairing">
        <p className="modal-copy">Keep the phone and ZimaOS on the same LAN. On Android, open Wireless debugging → Pair device with QR code.</p>
        {qrImage ? <>
          <div className="qr-frame"><img src={qrImage} alt="Temporary ADB wireless pairing QR code" /></div>
          <p className="qr-session-name"><i />Waiting for <code>{qrSession?.service_name}</code> · expires in two minutes</p>
          <ol>
            <li>Scan this code with Android's wireless-debugging scanner.</li>
            <li>Wait for the scanner to close.</li>
            <li>Click Complete pairing below.</li>
          </ol>
          <div className="form-actions qr-actions">
            <button type="button" disabled={qrBusy} onClick={() => void generateQr()}>Generate another</button>
            <button className="primary-action" type="button" disabled={qrBusy} onClick={() => void completeQr()}>{qrBusy && <LoaderCircle size={15} className="spin" />}Complete pairing</button>
          </div>
        </> : <button className="qr-generate" type="button" disabled={qrBusy} onClick={() => void generateQr()}>
          {qrBusy ? <LoaderCircle size={22} className="spin" /> : <QrCodeIcon size={28} />}
          <span><strong>Generate secure QR code</strong><small>One-time session, valid for two minutes</small></span>
        </button>}
        <p className="form-hint">QR pairing depends on local mDNS discovery. Use the six-digit method if ZimaOS and Android are on different networks.</p>
      </section>}
    </ModalShell>
  );
}

function EnvironmentModal({ devices, form, busy, onChange, onClose, onSubmit }: { devices: Device[]; form: EnvironmentForm; busy: boolean; onChange: (form: EnvironmentForm) => void; onClose: () => void; onSubmit: (event: FormEvent) => void }) {
  return <ModalShell titleId="environment-modal-title" onClose={onClose}><p className="kicker">Existing profile</p><h2 id="environment-modal-title">Register Linux Deploy</h2><p className="modal-copy">This links an existing Linux Deploy profile. It does not install or delete a distribution.</p><form onSubmit={onSubmit}><label>Android device<select required value={form.device_id} onChange={(event) => onChange({ ...form, device_id: event.target.value })}><option value="">Select a connected rooted device</option>{devices.map((device) => <option value={device.id} key={device.id}>{device.name}</option>)}</select></label><label>Display name<input required value={form.name} placeholder="Debian server" onChange={(event) => onChange({ ...form, name: event.target.value })} /></label><label>Linux Deploy profile<input required pattern="[A-Za-z0-9._-]+" value={form.profile} onChange={(event) => onChange({ ...form, profile: event.target.value })} /></label><label>Default shell user<input required pattern="[A-Za-z0-9._-]+" value={form.default_user} onChange={(event) => onChange({ ...form, default_user: event.target.value })} /></label><FormActions busy={busy} label="Register environment" onCancel={onClose} /></form></ModalShell>;
}

function FormActions({ busy, label, onCancel }: { busy: boolean; label: string; onCancel: () => void }) {
  return <div className="form-actions"><button type="button" onClick={onCancel}>Cancel</button><button className="primary-action" disabled={busy} type="submit">{busy && <LoaderCircle size={15} className="spin" />}{label}</button></div>;
}
