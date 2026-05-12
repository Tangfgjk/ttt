export type TrainingStage = "junior" | "senior";
export type TrainingScope = "none" | "junior" | "senior" | "both";

export type TrainingStatusResponse = {
  user_id: number;
  training_scope: TrainingScope;
  available_stages: TrainingStage[];
  junior_completed: boolean;
  senior_completed: boolean;
};

export type TrainingCompetencyDefinition = {
  code: string;
  name: string;
  definition: string;
  focus_tip: string;
};

export type TrainingQuestion = {
  question_id: number;
  stem_text: string;
  subject_name: string;
  grade_name?: string | null;
  question_type_name?: string | null;
  answer_text?: string | null;
  solution_text?: string | null;
};

export type TrainingGuideExampleCompetency = {
  competency_id: number;
  competency_name: string;
  level_value: number;
  definition: string;
  focus_tip: string;
  level_reason: string;
};

export type TrainingGuideExample = {
  question_id: number;
  stem_text: string;
  subject_name: string;
  grade_name?: string | null;
  question_type_name?: string | null;
  answer_text?: string | null;
  solution_text?: string | null;
  coach_tip: string;
  competencies: TrainingGuideExampleCompetency[];
};

export type TrainingModuleResponse = {
  stage: TrainingStage;
  title: string;
  summary: string;
  pass_threshold: number;
  required_question_count: number;
  competency_definitions: TrainingCompetencyDefinition[];
  guide_examples: TrainingGuideExample[];
  questions: TrainingQuestion[];
};

export type TrainingCompetencyAnswer = {
  competency_id: number;
  level_value: number;
};

export type TrainingQuestionAnswer = {
  question_id: number;
  competencies: TrainingCompetencyAnswer[];
};

export type TrainingSubmitRequest = {
  user_id: number;
  stage: TrainingStage;
  answers: TrainingQuestionAnswer[];
};

export type TrainingQuestionResult = {
  question_id: number;
  score_percent: number;
  is_passed: boolean;
  expected_competency_names: string[];
  predicted_competency_names: string[];
};

export type TrainingSubmitResponse = {
  stage: TrainingStage;
  passed: boolean;
  score_percent: number;
  pass_threshold: number;
  training_scope: TrainingScope;
  attempt_no: number;
  completed_at: string;
  question_results: TrainingQuestionResult[];
};
