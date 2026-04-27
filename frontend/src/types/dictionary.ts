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
