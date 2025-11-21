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
}

