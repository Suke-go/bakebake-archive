import type {
  GeneratePayload,
  GenerationResponse,
  LoraInfo,
  PublishPayload,
  PublishResponse,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || `Request failed with ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchLoras(): Promise<LoraInfo[]> {
  const res = await fetch(`${API_BASE}/lora`);
  return handleResponse(res);
}

export async function generateImages(payload: GeneratePayload): Promise<GenerationResponse> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

export async function publishYokai(payload: PublishPayload): Promise<PublishResponse> {
  const res = await fetch(`${API_BASE}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}

