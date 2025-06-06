#include <bits/stdc++.h>

using namespace std;
 
int main() {
    long long n;
    long long c;
    cin >> n;
    cin >> c;
    long long b = 1;
    while(n--) {
        b *= 10;
    }
    
    long long g = gcd<int64_t>(c, b);
    c /= g;
    b /= g;
    
    long long INF = 1'000'000;
    
    if (c < INF && b < INF && c > 0) {
        cout << "YES" << endl << c << " " << b;
    } else {
        cout << "NO";
    }
}