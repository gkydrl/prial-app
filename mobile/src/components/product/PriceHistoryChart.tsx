import React from 'react';
import { View, Text, Dimensions } from 'react-native';
import { LineChart } from 'react-native-gifted-charts';
import { Colors } from '@/constants/colors';
import { formatTRY } from '@/utils/currency';
import { formatChartLabel } from '@/utils/date';
import type { PriceHistoryPoint } from '@/types/api';

interface PriceHistoryChartProps {
  data: PriceHistoryPoint[];
}

export function PriceHistoryChart({ data }: PriceHistoryChartProps) {
  if (data.length === 0) {
    return (
      <View className="h-32 items-center justify-center">
        <Text className="text-muted text-sm">Fiyat geçmişi bulunamadı</Text>
      </View>
    );
  }

  const chartData = [...data].reverse().map((point) => ({
    value: point.price,
    label: formatChartLabel(point.recorded_at),
    dataPointText: '',
  }));

  const width = Dimensions.get('window').width - 48;

  return (
    <View>
      <LineChart
        data={chartData}
        width={width}
        height={160}
        color={Colors.brand}
        thickness={2}
        startFillColor={Colors.brand}
        endFillColor="transparent"
        startOpacity={0.3}
        endOpacity={0}
        areaChart
        curved
        hideDataPoints={chartData.length > 30}
        xAxisColor={Colors.border}
        yAxisColor={Colors.border}
        xAxisLabelTextStyle={{ color: Colors.muted, fontSize: 10 }}
        yAxisTextStyle={{ color: Colors.muted, fontSize: 10 }}
        backgroundColor="transparent"
        rulesColor={Colors.border}
        noOfSections={4}
        yAxisLabelPrefix="₺"
        hideYAxisText={false}
        showXAxisIndices={false}
        maxValue={Math.max(...chartData.map((d) => d.value)) * 1.1}
      />
    </View>
  );
}
