import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase/client';

export const useData = <T,>(tableName: string) => {
  const [data, setData] = useState<T[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data, error } = await supabase.from(tableName).select('*');
        if (error) throw error;
        setData(data as T[]);
      } catch (error: any) {
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [tableName]);

  return { data, loading, error };
};