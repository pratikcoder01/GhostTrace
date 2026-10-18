import { z } from 'zod';

export const caseCreateSchema = z.object({
  case_name: z
    .string()
    .min(3, 'Case name must be at least 3 characters')
    .max(120, 'Case name cannot exceed 120 characters'),
  description: z.string().max(500, 'Description cannot exceed 500 characters').optional(),
  network: z.enum(['simulated', 'bitcoin', 'ethereum'] as const, {
    error: 'Please select a valid network',
  }),
  data_source: z.string().min(1, 'Please select an intelligence data source'),
  seed_address_raw: z
    .string()
    .min(3, 'At least one seed wallet address is required')
    .refine((val) => val.trim().length > 0, 'Seed address cannot be blank'),
});

export type CaseCreateFormData = z.infer<typeof caseCreateSchema>;

export const mlPredictSchema = z.object({
  tx_id: z.string().optional(),
  network: z.enum(['bitcoin', 'ethereum', 'simulated'] as const).default('bitcoin'),
  features_raw: z
    .string()
    .min(1, 'Feature vector is required')
    .refine((val) => {
      try {
        const parsed = JSON.parse(val);
        return Array.isArray(parsed) && parsed.length > 0 && parsed.every((x) => typeof x === 'number');
      } catch {
        // Also allow comma-separated numbers
        const parts = val.split(',').map((p) => p.trim());
        return parts.length > 0 && parts.every((p) => !isNaN(Number(p)) && p !== '');
      }
    }, 'Features must be a valid JSON array or comma-separated list of numbers'),
});
