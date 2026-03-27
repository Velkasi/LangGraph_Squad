import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export const useOrganization = (orgId: string) => {
  return useQuery({
    queryKey: ['organization', orgId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('organizations')
        .select('*')
        .eq('id', orgId)
        .single();
      
      if (error) throw error;
      return data;
    },
    enabled: !!orgId,
  });
};