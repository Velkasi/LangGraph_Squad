import { useQuery } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export const useOrganization = (organizationId: string) => {
  return useQuery<Organization, Error>({
    queryKey: ['organization', organizationId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('organizations')
        .select('id, name, created_at')
        .eq('id', organizationId)
        .single();
      
      if (error) throw error;
      
      return data;
    },
    enabled: !!organizationId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
};