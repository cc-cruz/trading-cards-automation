declare module 'next/app' {
  import { NextComponentType, NextPageContext } from 'next';
  import { AppProps as NextAppProps } from 'next/dist/shared/lib/router/router';

  export type AppProps<P = {}> = {
    Component: NextComponentType<NextPageContext, any, P>;
    router: NextAppProps['router'];
    __N_SSG?: boolean;
    __N_SSP?: boolean;
    pageProps: P;
  };
}

// Add dual-side upload interfaces and enhanced card data types

export interface DualSideCardData {
  player: string;
  set: string;
  year: string;
  card_number: string;
  parallel: string;
  manufacturer: string;
  features: string;
  graded: boolean;
  grade: string;
  grading_company: string;
  cert_number: string;
  confidence_score: number;
  dual_side: boolean;
  ocr_sources: string;
}

export interface UploadMode {
  type: 'single' | 'dual' | 'auto';
  description: string;
  confidence_boost: string;
}

export interface FileUploadState {
  id: string;
  file: File;
  preview: string;
  side: 'front' | 'back';
  paired_with?: string;
  upload_status: 'pending' | 'uploading' | 'uploaded' | 'failed';
  upload_progress: number;
  gcs_url?: string;
}

export interface CardProcessingResult {
  card_id: string;
  card_data: DualSideCardData;
  price_data: PriceData;
  front_image_url: string;
  back_image_url?: string;
  processing_time_ms?: number;
}

export interface UploadStep {
  step: 'select' | 'upload' | 'process' | 'complete';
  description: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  error?: string;
} 