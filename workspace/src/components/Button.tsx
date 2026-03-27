import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
}

export default function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  fullWidth = false,
}: ButtonProps) {
  const variantStyles = styles[variant];
  const sizeStyles = styles[size];
  const isDisabled = disabled || loading;

  return (
    <TouchableOpacity
      style={[
        styles.button,
        variantStyles,
        sizeStyles,
        fullWidth && styles.fullWidth,
        isDisabled && styles.disabled,
      ]}
      onPress={onPress}
      disabled={isDisabled}
      accessibilityState={{ disabled: isDisabled }}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'outline' ? '#3498db' : 'white'} />
      ) : (
        <Text style={[styles.text, variant === 'outline' && styles.textOutline]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 100,
  },
  primary: {
    backgroundColor: '#3498db',
  },
  secondary: {
    backgroundColor: '#e74c3c',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#3498db',
  },
  small: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    minWidth: 80,
  },
  medium: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    minWidth: 100,
  },
  large: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    minWidth: 120,
  },
  fullWidth: {
    width: '100%',
  },
  disabled: {
    opacity: 0.6,
  },
  text: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  textOutline: {
    color: '#3498db',
  },
});