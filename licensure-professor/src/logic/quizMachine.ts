/**
 * Quiz session state machine (pure reducer; unit tested).
 *
 * select -> submit (blocked with an inline error if nothing is selected)
 * -> the correct answer and explanation are shown -> next -> ... -> finished.
 */

export const SELECT_ERROR = 'Select an answer to continue';

export interface QuizState {
  questionIds: string[];
  index: number;
  selected: string | null;
  submitted: boolean;
  error: string | null;
  answers: Record<string, string>; // questionId -> selectedOptionId
  finished: boolean;
  timedOut: boolean;
}

export type QuizAction =
  | { type: 'select'; optionId: string }
  | { type: 'submit' }
  | { type: 'next' }
  | { type: 'timeout' }
  | { type: 'restart' };

export function initialQuizState(questionIds: string[]): QuizState {
  return { questionIds, index: 0, selected: null, submitted: false, error: null,
           answers: {}, finished: false, timedOut: false };
}

export function quizReducer(state: QuizState, action: QuizAction): QuizState {
  if (state.finished && action.type !== 'restart') return state;
  switch (action.type) {
    case 'select':
      if (state.submitted) return state; // answer is locked after submit
      return { ...state, selected: action.optionId, error: null };
    case 'submit': {
      if (state.submitted) return state;
      if (!state.selected) return { ...state, error: SELECT_ERROR };
      const qid = state.questionIds[state.index];
      return { ...state, submitted: true, error: null,
               answers: { ...state.answers, [qid]: state.selected } };
    }
    case 'next': {
      if (!state.submitted) return state;
      if (state.index >= state.questionIds.length - 1) return { ...state, finished: true };
      return { ...state, index: state.index + 1, selected: null, submitted: false, error: null };
    }
    case 'timeout':
      return { ...state, finished: true, timedOut: true };
    case 'restart':
      return initialQuizState(state.questionIds);
  }
}

export function isLastQuestion(state: QuizState): boolean {
  return state.index >= state.questionIds.length - 1;
}
