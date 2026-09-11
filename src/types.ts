export type Kind = "content" | "added" | "removed" | "wording" | "uncertain";
export type Report = {
  id: string;
  companyId: string;
  year: number;
  receipt: string | null;
  filedAt: string | null;
  corrected: boolean;
  checkedAt: string | null;
  sha256: string;
  dartUrl: string | null;
};
export type EvidenceBlock = {
  id: string;
  reportId: string;
  kind: "paragraph" | "table";
  section: string;
  order: number;
  text: string;
  normalized: string;
  contextBefore: string;
  contextAfter: string;
  headers?: string[];
  rows?: string[][];
  unit?: string;
};
export type Citation = { blockId: string; quote: string };
export type Change = {
  id: string;
  kind: Kind;
  section: string;
  title: string;
  explanation: string;
  before: Citation[];
  after: Citation[];
  reviewStatus: "approved" | "needs_review";
};
export type Financial = {
  id: string;
  label: string;
  before: string;
  after: string;
  delta: string;
  percent: string | null;
  status: string;
  reason: string | null;
  beforeBlockId: string;
  afterBlockId: string;
  beforeRow?: number;
  afterRow?: number;
  currency: "KRW";
  basis: "CFS";
};
export type Comparison = {
  schemaVersion: 1;
  id: string;
  companyId: string;
  companyName: string;
  stockCode: string;
  mode: "demo" | "reviewed";
  version: string;
  checkedAt: string | null;
  reports: [Report, Report];
  financials: Financial[];
  changes: Change[];
  evidence: EvidenceBlock[];
  analysis: { model: string; promptVersion: string };
  coverage: string[];
};
export type Catalog = {
  schemaVersion: 1;
  companies: {
    id: string;
    name: string;
    stockCode: string;
    comparisons: {
      id: string;
      years: [number, number];
      path: string;
      mode: "demo" | "reviewed";
    }[];
  }[];
};
