export type RecurrenceType = 'daily' | 'weekly' | 'monthly';

export interface Schedule {
  recurrenceType: RecurrenceType;
  enabled: boolean;
  executionTime: string;
  timezone: string;
  dayOfWeek: number | null;
  dayOfMonth: number | null;
}

export type ScheduleCandidate = Schedule;

export interface NextOccurrence {
  instant: string;
  timezone: string;
  localDateTime: string;
}

export interface ScheduleEnvelope {
  schedule: Schedule | null;
  nextOccurrence: NextOccurrence | null;
}

export interface SchedulePreviewEnvelope {
  nextOccurrence: NextOccurrence | null;
}
