import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';

export const useCurrentUser = () => {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const { data: { user }, error: authError } = await supabase.auth.getUser();
      
      if (authError || !user) {
        throw new Error('Not authenticated');
      }
      
      const { data, error: dbError } = await supabase
        .from('users')
        .select('id, email, role, organization_id')
        .eq('auth_uid', user.id)
        .single();
      
      if (dbError) {
        throw dbError;
      }
      
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
};