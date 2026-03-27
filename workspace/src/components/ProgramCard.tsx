import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Program } from '../types/db';

interface ProgramCardProps {
  program: Program;
  onPress: () => void;
}

const ProgramCard: React.FC<ProgramCardProps> = ({ program, onPress }) => {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <Text style={styles.title} numberOfLines={2}>
        {program.title}
      </Text>
      <Text style={styles.description} numberOfLines={3}>
        {program.description}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginVertical: 8,
    marginHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  description: {
    fontSize: 14,
    color: '#666',
  },
});

export default ProgramCard;