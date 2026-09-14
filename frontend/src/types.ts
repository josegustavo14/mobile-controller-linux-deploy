export type Status = "CONNECTED" | "DISCONNECTED" | "CONNECTING" | "RECONNECTING" | "ERROR";
export type EnvironmentStatus = "RUNNING" | "STOPPED" | "ERROR" | "UNKNOWN";
export type View =
  | "dashboard"
  | "devices"
  | "android"
  | "scrcpy"
  | "environments"
  | "services"
  | "terminal"
  | "logs"
  | "settings";

export type Device = {
  id: string;
  name: string;
  host: string;
  port: number;
  serial: string | null;
  connection_status: Status;
  manufacturer: string | null;
  model: string | null;
  android_version: string | null;
  sdk: string | null;
  hardware: string | null;
  cpu_abi: string | null;
  display_id: string | null;
  kernel: string | null;
  root_available: boolean | null;
  last_error: string | null;
  details_updated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Environment = {
  id: string;
  device_id: string;
  name: string;
  profile: string;
  default_user: string;
  status: EnvironmentStatus;
  last_output: string | null;
  created_at: string;
  updated_at: string;
};

export type AuditLog = {
  id: string;
  action: string;
  level: string;
  device_id: string | null;
  message: string;
  created_at: string;
};

export type Dashboard = {
  total_devices: number;
  connected_devices: number;
  rooted_devices: number;
  devices_with_errors: number;
  recent_activity: AuditLog[];
};

export type SystemInfo = {
  version: string;
  authentication_enabled: boolean;
  adb_path: string;
  adb_server_port: number;
  adb_timeout: number;
  scrcpy_path: string;
  scrcpy_viewer_port: number;
  termux_agent_configured: boolean;
  termux_agent_port: number;
  linux_deploy_cli: string;
  database_backend: string;
};

export type ScrcpyStatus = {
  running: boolean;
  device_id: string | null;
  serial: string | null;
  viewer_port: number;
  password: string | null;
  message: string;
};

export type TermuxCapabilities = {
  sensors: string[];
  apis: string[];
};

export type TermuxData = {
  source: string;
  payload: unknown;
};

export type UpdateStatus = {
  current_version: string;
  latest_version: string | null;
  update_available: boolean;
  updater_enabled: boolean;
  message: string;
};

export type ServiceInfo = {
  name: string;
  running: boolean | null;
  raw: string;
};

export type DeviceDiagnostics = {
  battery_level: number | null;
  battery_status: string | null;
  charging: boolean | null;
  temperature_c: number | null;
  uptime_seconds: number | null;
  screen_state: string | null;
  wifi_ipv4: string | null;
  tailscale_ipv4: string | null;
  termux_installed: boolean;
  tailscale_installed: boolean;
  storage: string;
};
