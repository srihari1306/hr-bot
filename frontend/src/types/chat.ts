export interface Citation {
  heading: string;
  url: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  citations?: Citation[];
  suggestedQuestions?: string[];
  turnId?: string;
}
