import { useQuery } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

export interface CurrentUser {
  id: string;
  email: string;
  role: 'admin' | 'practitioner' | 'patient';
  organization_id: string;
}

export const useCurrentUser = () => {
  return useQuery<CurrentUser, Error>({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const { data: { user }, error: authError } = await supabase.auth.getUser();
      
      if (authError) throw authError;
      if (!user) throw new Error('No user logged in');
      
      const { data, error } = await supabase
        .from('users')
        .select('id, email, role, organization_id')
        .eq('auth_uid', user.id)
        .single();
      
      if (error) throw error;
      
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    cacheTime: 1000 * 60 * 30, // 30 minutes
  });
};