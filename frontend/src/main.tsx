import {
  Activity,
  Boxes,
  Cable,
  FileText,
  Link,
  LoaderCircle,
  MonitorCog,
  Pencil,
  Plus,
  Power,
  Radio,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Smartphone,
  TerminalSquare,
  Trash2,
  Wifi,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Status = "CONNECTED" | "DISCONNECTED" | "CONNECTING" | "RECONNECTING" | "ERROR";
type Device = {
  id: string;
  name: string;
  host: string;
  port: number;
  connection_status: Status;
  manufacturer: string | null;
  model: string | null;
  android_version: string | null;
  cpu_abi: string | null;
  kernel: string | null;
  root_available: boolean | null;
  last_error: string | null;
};
type DeviceForm = { name: string; host: string; port: string };
type PairForm = { host: string; port: string; pairing_code: string };
type Modal = "device" | "pair" | null;

const navigation = [
  [Activity, "Dashboard"],
  [Cable, "Devices"],
  [Boxes, "Environments"],
  [MonitorCog, "Services"],
  [TerminalSquare, "Terminal"],
  [FileText, "Logs"],
  [Settings2, "Settings"],
] as const;
const emptyDeviceForm: DeviceForm = { name: "", host: "", port: "5555" };
const emptyPairForm: PairForm = { host: "", port: "", pairing_code: "" };
const labels: Record<Status, string> = {
  CONNECTED: "Connected",
  DISCONNECTED: "Disconnected",
  CONNECTING: "Connecting",
  RECONNECTING: "Reconnecting",
  ERROR: "Connection error",
};

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload.detail === "string" ? payload.detail : "Device operation failed.";
    throw new Error(detail);
  }
  return payload as T;
}

function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [deviceForm, setDeviceForm] = useState<DeviceForm>(emptyDeviceForm);
  const [pairForm, setPairForm] = useState<PairForm>(emptyPairForm);
  const [editing, setEditing] = useState<Device | null>(null);
  const [modal, setModal] = useState<Modal>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async () => setDevices(await api<Device[]>("/api/devices"));
  useEffect(() => {
    void load().catch((error: Error) => setNotice(error.message));
  }, []);

  const openCreate = () => {
    setEditing(null);
    setDeviceForm(emptyDeviceForm);
    setModal("device");
  };

  const openEdit = (device: Device) => {
    setEditing(device);
    setDeviceForm({ name: device.name, host: device.host, port: String(device.port) });
    setModal("device");
  };

  const saveDevice = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("save");
    setNotice(null);
    try {
      const payload = { ...deviceForm, port: Number(deviceForm.port) };
      const saved = await api<Device>(editing ? `/api/devices/${editing.id}` : "/api/devices", {
        method: editing ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setDevices((current) =>
        editing ? current.map((item) => (item.id === saved.id ? saved : item)) : [saved, ...current],
      );
      setModal(null);
      setNotice(editing ? "Device settings saved." : "Android device added. Connect when it is online.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not save this Android device.");
    } finally {
      setBusy(null);
    }
  };

  const pairDevice = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("pair");
    setNotice(null);
    try {
      const response = await api<{ message: string }>("/api/devices/pair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...pairForm, port: Number(pairForm.port) }),
      });
      setPairForm(emptyPairForm);
      setModal(null);
      setNotice(response.message);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Wireless pairing failed.");
    } finally {
      setBusy(null);
    }
  };

  const action = async (device: Device, operation: "connect" | "disconnect" | "refresh" | "reboot") => {
    setBusy(`${operation}-${device.id}`);
    setNotice(null);
    try {
      const payload = await api<Device | { device: Device; message: string }>(
        `/api/devices/${device.id}/${operation}`,
        { method: "POST" },
      );
      const updated = "device" in payload ? payload.device : payload;
      setDevices((current) => current.map((item) => (item.id === device.id ? updated : item)));
      setNotice("message" in payload ? payload.message : "Device details refreshed.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Device operation failed.");
    } finally {
      setBusy(null);
    }
  };

  const removeDevice = async (device: Device) => {
    if (!window.confirm(`Remove ${device.name} from this control plane?`)) return;
    setBusy(`delete-${device.id}`);
    setNotice(null);
    try {
      await api<null>(`/api/devices/${device.id}`, { method: "DELETE" });
      setDevices((current) => current.filter((item) => item.id !== device.id));
      setNotice("Device removed.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not remove this device.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <main className="shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Android Server Manager home">
          <span className="brand-mark">A</span>
          <span>Android<br />Server Manager</span>
        </a>
        <nav aria-label="Primary navigation">
          {navigation.map(([Icon, label], index) => (
            <a
              className={index === 1 ? "nav-item active" : "nav-item disabled"}
              href={index === 1 ? "/" : "#"}
              key={label}
              aria-disabled={index !== 1}
              onClick={(event) => index !== 1 && event.preventDefault()}
            >
              <Icon size={18} />{label}
            </a>
          ))}
        </nav>
        <div className="node-state"><i />Wi-Fi control plane ready</div>
      </aside>

      <section className="workspace">
        <header>
          <div>
            <p className="kicker">Device registry</p>
            <h1>Android compute nodes</h1>
            <p className="lede">Connect trusted Android devices over your private Wi-Fi network and inspect their root capability.</p>
          </div>
          <div className="header-actions">
            <button className="secondary-action" type="button" onClick={() => setModal("pair")}>
              <Radio size={17} />Pair wirelessly
            </button>
            <button className="primary-action" type="button" onClick={openCreate}>
              <Plus size={17} />Add device
            </button>
          </div>
        </header>

        {notice && (
          <div className="notice" role="status">
            {notice}
            <button type="button" aria-label="Dismiss message" onClick={() => setNotice(null)}><X size={16} /></button>
          </div>
        )}
        <div className="rule" />

        {devices.length === 0 ? (
          <section className="empty-state">
            <div className="device-orbit"><Wifi size={34} /></div>
            <div>
              <h2>No Android nodes enrolled</h2>
              <p>Use classic ADB on port 5555, or pair Android 11 and newer with a wireless debugging code.</p>
              <div className="empty-actions">
                <button className="primary-action" type="button" onClick={openCreate}><Plus size={17} />Add first device</button>
                <button className="text-action" type="button" onClick={() => setModal("pair")}><Link size={16} />Pair first</button>
              </div>
            </div>
          </section>
        ) : (
          <section className="device-grid">
            {devices.map((device) => (
              <article className="device-card" key={device.id}>
                <div className="card-top">
                  <div className="device-name">
                    <span className="phone-icon"><Smartphone size={20} /></span>
                    <div>
                      <h2>{device.name}</h2>
                      <p>{device.manufacturer && device.model ? `${device.manufacturer} ${device.model}` : "Awaiting inspection"}</p>
                    </div>
                  </div>
                  <span className={`status ${device.connection_status.toLowerCase()}`}><i />{labels[device.connection_status]}</span>
                </div>
                <div className="device-specs">
                  <span><Wifi size={15} />{device.host}:{device.port}</span>
                  <span><ShieldCheck size={15} />{device.root_available === null ? "Root not checked" : device.root_available ? "Root available" : "Root unavailable"}</span>
                  {device.android_version && <span>Android {device.android_version} · {device.cpu_abi}</span>}
                  {device.kernel && <span>Kernel {device.kernel}</span>}
                </div>
                {device.last_error && <p className="device-error">{device.last_error}</p>}
                <div className="card-actions">
                  {device.connection_status === "CONNECTED" ? (
                    <>
                      <button type="button" onClick={() => void action(device, "refresh")} disabled={busy !== null}>
                        <RefreshCw size={15} className={busy === `refresh-${device.id}` ? "spin" : ""} />Refresh
                      </button>
                      <button type="button" onClick={() => void action(device, "reboot")} disabled={busy !== null}>
                        <Power size={15} />Reboot
                      </button>
                      <button type="button" onClick={() => void action(device, "disconnect")} disabled={busy !== null}>Disconnect</button>
                    </>
                  ) : (
                    <button className="connect-button" type="button" onClick={() => void action(device, "connect")} disabled={busy !== null}>
                      {busy === `connect-${device.id}` ? <LoaderCircle size={15} className="spin" /> : <Cable size={15} />}Connect ADB
                    </button>
                  )}
                </div>
                <div className="card-management">
                  <button type="button" onClick={() => openEdit(device)} disabled={busy !== null}><Pencil size={14} />Edit</button>
                  <button className="danger-subtle" type="button" onClick={() => void removeDevice(device)} disabled={busy !== null}><Trash2 size={14} />Remove</button>
                </div>
              </article>
            ))}
          </section>
        )}
      </section>

      {modal === "device" && (
        <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setModal(null)}>
          <section className="device-modal" role="dialog" aria-modal="true" aria-labelledby="device-modal-title">
            <button className="close-modal" type="button" onClick={() => setModal(null)} aria-label="Close"><X size={18} /></button>
            <p className="kicker">Wi-Fi endpoint</p>
            <h2 id="device-modal-title">{editing ? "Edit Android device" : "Add Android device"}</h2>
            <p className="modal-copy">Use the connection address shown by wireless debugging, or port 5555 for classic ADB over TCP.</p>
            <form onSubmit={saveDevice}>
              <label>Name<input required value={deviceForm.name} placeholder="S20+" onChange={(event) => setDeviceForm({ ...deviceForm, name: event.target.value })} /></label>
              <label>Host<input required value={deviceForm.host} placeholder="192.168.15.98 or 100.x.x.x" onChange={(event) => setDeviceForm({ ...deviceForm, host: event.target.value })} /></label>
              <label>ADB connection port<input required type="number" min="1" max="65535" value={deviceForm.port} onChange={(event) => setDeviceForm({ ...deviceForm, port: event.target.value })} /></label>
              <div className="form-actions">
                <button type="button" onClick={() => setModal(null)}>Cancel</button>
                <button className="primary-action" disabled={busy === "save"} type="submit">
                  {busy === "save" && <LoaderCircle size={15} className="spin" />}{editing ? "Save changes" : "Add device"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}

      {modal === "pair" && (
        <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setModal(null)}>
          <section className="device-modal" role="dialog" aria-modal="true" aria-labelledby="pair-modal-title">
            <button className="close-modal" type="button" onClick={() => setModal(null)} aria-label="Close"><X size={18} /></button>
            <p className="kicker">Android 11 or newer</p>
            <h2 id="pair-modal-title">Pair wireless debugging</h2>
            <p className="modal-copy">On Android, open Wireless debugging → Pair device with pairing code. Enter that temporary address and code here.</p>
            <form onSubmit={pairDevice}>
              <label>Pairing host<input required value={pairForm.host} placeholder="192.168.15.98" onChange={(event) => setPairForm({ ...pairForm, host: event.target.value })} /></label>
              <label>Pairing port<input required type="number" min="1" max="65535" value={pairForm.port} placeholder="37123" onChange={(event) => setPairForm({ ...pairForm, port: event.target.value })} /></label>
              <label>Pairing code<input required inputMode="numeric" pattern="[0-9]{6}" minLength={6} maxLength={6} value={pairForm.pairing_code} placeholder="123456" onChange={(event) => setPairForm({ ...pairForm, pairing_code: event.target.value })} /></label>
              <p className="form-hint">After pairing, add the device using the separate IP address and connection port shown on the Wireless debugging screen.</p>
              <div className="form-actions">
                <button type="button" onClick={() => setModal(null)}>Cancel</button>
                <button className="primary-action" disabled={busy === "pair"} type="submit">
                  {busy === "pair" && <LoaderCircle size={15} className="spin" />}Pair device
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
