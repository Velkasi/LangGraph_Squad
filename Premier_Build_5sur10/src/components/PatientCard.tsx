import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Patient } from '../types/db';

interface PatientCardProps {
  patient: Patient;
  onPress: () => void;
}

const PatientCard: React.FC<PatientCardProps> = ({ patient, onPress }) => {
  return (
    <TouchableOpacity style={styles.card} onPress={onPress}>
      <Text style={styles.name}>
        {patient.user?.full_name || 'Patient'}
      </Text>
      <Text style={styles.email}>
        {patient.user?.email}
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
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
    color: '#666',
  },
});

export default PatientCard;