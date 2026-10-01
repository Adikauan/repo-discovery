import type { ReactNode } from 'react';

export type PrimarySection = 'home' | 'monitoring-configurations' | 'executions' | 'settings';
export interface NavigationItem { id: PrimarySection; label: string; path: string; icon: ReactNode; matchPaths: string[] }
export interface BreadcrumbItem { label: string; path?: string; current?: boolean }
export interface RouteDescriptor { id: string; path: string; title: string; primarySection: PrimarySection; breadcrumbs?: BreadcrumbItem[] }
export type PageStateKind = 'loading' | 'empty' | 'error' | 'disabled' | 'success' | 'placeholder';
export interface PageStateDescriptor { kind: PageStateKind; title?: string; message: string; action?: ReactNode; liveMode?: 'polite' | 'assertive' }
export type PresentationStatus = 'active' | 'enabled' | 'disabled' | 'paused' | 'pending' | 'running' | 'completed' | 'partially-completed' | 'failed';
export type WizardStepState = 'upcoming' | 'current' | 'completed';
export interface WizardStepDescriptor { id: string; label: string; description?: string; state: WizardStepState }
