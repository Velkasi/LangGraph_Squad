import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

type Pathology = {
  id: string;
  organization_id: string | null;
  name: string;
  description: string | null;
  created_at: string;
};

export function usePathologies() {
  return useQuery<Pathology[], Error>({
    queryKey: ['pathologies'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('pathologies')
        .select('*')
        .order('name');

      if (error) {
        console.error('Error fetching pathologies:', error);
        throw error;
      }

      return data;
    },
  });
}