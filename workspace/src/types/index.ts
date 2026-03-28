export type UUID = string;

export interface Profile {
  id: UUID;
  email: string;
  full_name?: string;
  avatar_url?: string;
  created_at: string;
}

export interface Product {
  id: UUID;
  name: string;
  description?: string;
  price: number;
  image_url?: string;
  category?: string;
  created_at: string;
}

export interface OrderItem {
  id: UUID;
  order_id: UUID;
  product_id: UUID;
  quantity: number;
  price: number;
  created_at: string;
}

export interface Order {
  id: UUID;
  user_id: UUID;
  total: number;
  status: 'pending' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
  created_at: string;
  items?: OrderItem[];
}

export interface PaginatedResponse<T> {
  data: T[];
  count: number;
  error?: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface ServiceResponse<T> {
  data: T | null;
  error: string | null;
  success: boolean;
}

// Form types
export interface ProductForm {
  name: string;
  description?: string;
  price: number;
  image_url?: string;
  category?: string;
}

export interface OrderForm {
  items: {
    product_id: UUID;
    quantity: number;
  }[];
}