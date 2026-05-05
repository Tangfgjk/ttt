export type DictionaryItem = {
  id: number;
  code: string;
  name: string;
};

export type GradeItem = {
  id: number;
  grade_index: number;
  grade_code?: string | null;
  grade_name: string;
  edu_stage?: string | null;
};

export type CognitiveLevelItem = {
  id: number;
  code: string;
  name: string;
  level_order: number;
};

export type CompetencyItem = {
  id: number;
  code: string;
  name: string;
  display_order: number;
};
