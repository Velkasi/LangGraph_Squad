import { useState, useEffect } from 'react';
import { useCurrentUser } from './useCurrentUser';
import { supabase } from '../lib/supabase';

interface PatientProgram {
  id: string;
  patient_id: string;
  program_id: string;
  assigned_by: string;
  assigned_at: string;
  mode: 'manual' | 'auto';
  program: {
    id: string;
    title: string;
    description: string;
    pathology_id: string;
  };
}

export function usePatientPrograms() {
  const { user, loading: userLoading } = useCurrentUser();
  const [programs, setPrograms] = useState<PatientProgram[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function getPrograms() {
      if (!user || user.role !== 'patient') {
        setPrograms([]);
        setLoading(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('patient_programs')
          .select(`
            id,
            patient_id,
            program_id,
            assigned_by,
            assigned_at,
            mode,
            program:programs!inner(
              id,
              title,
              description,
              pathology_id
            )
          `)
          .eq('patient_id', user.id);

        if (error) throw error;

        setPrograms(data);
      } catch (error) {
        console.error('Error fetching patient programs:', error);
        setPrograms([]);
      } finally {
        setLoading(false);
      }
    }

    getPrograms();
  }, [user]);

  return { programs, loading: loading || userLoading };
}