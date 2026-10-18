// A fake Arduino for testing r1_io.ino on a laptop (18 Oct 2026). The REAL sketch is compiled against this file instead of
// the Arduino core: the clock, the pins, the analog inputs and the serial port are plain variables the test can set and read.
#pragma once
#include <cstdint>
#include <cstdlib>
#include <string>
#include <deque>

typedef uint8_t byte;
enum { LOW = 0, HIGH = 1, INPUT = 0, OUTPUT = 1, INPUT_PULLUP = 2, RISING = 3 };
const uint8_t A0 = 54, A1 = 55;
#define constrain(x, lo, hi) ((x) < (lo) ? (lo) : ((x) > (hi) ? (hi) : (x)))
#define digitalPinToInterrupt(p) (p)

// ---- the fake board's state, visible to the test
inline unsigned long g_ms = 0;                 // the clock
inline int g_pin[80] = {0};                    // digital pin levels (outputs written by the sketch, inputs set by the test)
inline int g_pwm[80] = {0};                    // analogWrite values
inline int g_adc[80] = {0};                    // analogRead values (set by the test)
inline unsigned long millis() { return g_ms; }
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWrite(uint8_t p, int v) { g_pin[p] = v ? 1 : 0; }
inline int digitalRead(uint8_t p) { return g_pin[p]; }
inline void analogWrite(uint8_t p, int v) { g_pwm[p] = v; }
inline int analogRead(uint8_t p) { return g_adc[p]; }
inline void attachInterrupt(uint8_t, void (*)(), int) {}
inline void noInterrupts() {}
inline void interrupts() {}

// ---- the parts of Arduino's String class the sketch uses
class String {
 public:
  std::string s;
  String() {}
  String(const char* c) : s(c) {}
  String(const std::string& x) : s(x) {}
  void trim() {
    size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
    s = (a == std::string::npos) ? "" : s.substr(a, b - a + 1);
  }
  unsigned int length() const { return (unsigned int)s.size(); }
  char charAt(unsigned int i) const { return i < s.size() ? s[i] : 0; }
  int indexOf(char c, unsigned int from = 0) const { size_t i = s.find(c, from); return i == std::string::npos ? -1 : (int)i; }
  String substring(unsigned int a) const { return a < s.size() ? String(s.substr(a)) : String(""); }
  String substring(unsigned int a, unsigned int b) const { return a < s.size() ? String(s.substr(a, b - a)) : String(""); }
  long toInt() const { return std::strtol(s.c_str(), nullptr, 10); }
  bool endsWith(const char* t) const { std::string x(t); return s.size() >= x.size() && s.compare(s.size() - x.size(), x.size(), x) == 0; }
  String& operator+=(char c) { s += c; return *this; }
  String& operator=(const char* c) { s = c; return *this; }
};

// ---- the serial port: the test pushes command lines in and reads the status lines out
struct FakeSerial {
  std::deque<char> in;
  std::string out;
  void begin(long) {}
  int available() { return (int)in.size(); }
  int read() { if (in.empty()) return -1; char c = in.front(); in.pop_front(); return c; }
  void print(const char* x) { out += x; }
  void print(char x) { out += x; }
  void print(long x) { out += std::to_string(x); }
  void print(int x) { out += std::to_string(x); }
  void println(int x) { out += std::to_string(x) + "\n"; }
  void send(const std::string& line) { for (char c : line) in.push_back(c); in.push_back('\n'); }
};
inline FakeSerial Serial;
