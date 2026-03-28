export type Book = {
  id: string;
  title: string;
  author: string;
  created_at: string;
  user_id: string;
};

export type User = {
  id: string;
  email: string;
  created_at: string;
};

export type Session = {
  user: User;
  access_token: string;
  refresh_token: string;
};