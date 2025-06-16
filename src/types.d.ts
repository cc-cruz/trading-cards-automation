declare module 'react-hot-toast' {
  import { ReactNode } from 'react';

  export interface ToasterProps {
    position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
    reverseOrder?: boolean;
    toastOptions?: {
      duration?: number;
      style?: React.CSSProperties;
      className?: string;
    };
  }

  export function Toaster(props?: ToasterProps): JSX.Element;
  export function toast(message: string | ReactNode, options?: any): string;
  export function toast.success(message: string | ReactNode, options?: any): string;
  export function toast.error(message: string | ReactNode, options?: any): string;
  export function toast.loading(message: string | ReactNode, options?: any): string;
  export function toast.dismiss(toastId?: string): void;
  export function toast.remove(toastId?: string): void;
  export function toast.promise<T>(
    promise: Promise<T>,
    messages: {
      loading: string | ReactNode;
      success: string | ReactNode;
      error: string | ReactNode;
    },
    options?: any
  ): Promise<T>;
}

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