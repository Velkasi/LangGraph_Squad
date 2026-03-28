import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';

export const useOrganization = (organizationId: string) => {
  return useQuery({
    queryKey: ['organization', organizationId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('organizations')
        .select('*')
        .eq('id', organizationId)
        .single();
      
      if (error) {
        throw error;
      }
      
      return data;
    },
    enabled: !!organizationId,
  });
};