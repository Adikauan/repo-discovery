export interface ProblemDetails {
  type?: string;
  title: string;
  status: number;
  code?: string;
  detail: string;
  errors?: Array<{ field: string; code: string; message: string }>;
}
