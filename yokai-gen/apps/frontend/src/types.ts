export interface LoraInfo {
  name: string;
  path: string;
}

export interface GenerationImage {
  base64_png: string;
  seed: number;
  width: number;
  height: number;
  lora: string[];
}

export interface GenerationResponse {
  images: GenerationImage[];
}

export interface GeneratePayload {
  prompt: string;
  negative_prompt?: string;
  steps?: number;
  guidance_scale?: number;
  num_images?: number;
  lora?: string[];
  seed?: number | null;
  width?: number;
  height?: number;
}

export interface PublishMetadata {
  title: string;
  description?: string;
  longitude: number;
  latitude: number;
  altitude?: number;
  color?: string;
  scale?: number;
  era?: "now" | "past";
  id?: string;
  source?: string;
}

export interface PublishPayload {
  metadata: PublishMetadata;
  image_base64: string;
  prompt?: string;
  negative_prompt?: string;
  seed?: number;
  lora?: string[];
}

export interface PublishResponse {
  id: string;
  image_url: string;
  image_path: string;
  places_path: string;
  places_count: number;
}

