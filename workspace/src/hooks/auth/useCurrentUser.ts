import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { User } from '@/types/db';

export const useCurrentUser = () => {
  return useQuery<User | null>({
    queryKey: ['current-user'],
    queryFn: async () => {
      const { data: { user } } = await supabase.auth.getUser();
      
      if (!user) return null;
      
      const { data, error } = await supabase
        .from('users')
        .select('*')
        .eq('auth_uid', user.id)
        .single();
      
      if (error) throw error;
      return data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};