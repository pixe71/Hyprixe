#pragma once

#include <algorithm>
#include <cmath>

namespace hyprixe {

// A percentage floor must round up in device units. Coarse devices also
// need a nonzero step when a positive percentage rounds down to zero.
inline int backlightTarget(int actual, int maximum, bool increase, double step, double floor) {
  if (maximum <= 0 || !std::isfinite(step) || step <= 0 || !std::isfinite(floor)) {
    return actual;
  }
  const int minimum = static_cast<int>(std::ceil(maximum * (std::clamp(floor, 0.0, 100.0) / 100)));
  const int delta = std::max(1, static_cast<int>(std::round(maximum * (std::min(step, 100.0) / 100))));
  const int current = std::clamp(actual, 0, maximum);
  if (increase) {
    return std::max(minimum, current + std::min(delta, maximum - current));
  }
  // A lower level may have been set outside Waybar. Leave it alone until
  // the user scrolls up rather than making a decrease brighten the screen.
  return current <= minimum ? current : std::max(minimum, current - delta);
}

}  // namespace hyprixe
