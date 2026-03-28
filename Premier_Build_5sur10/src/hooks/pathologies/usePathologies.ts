import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';
import { Pathology } from '../../types/db';

export const usePathologies = () => {
  return useQuery<Pathology[], Error>({
    queryKey: ['pathologies'],
    queryFn: async (): Promise<Pathology[]> => {
      const { data, error } = await supabase
        .from('pathologies')
        .select('*')
        .order('name');

      if (error) {
        throw error;
      }

      return data as Pathology[];
    },
  });
};