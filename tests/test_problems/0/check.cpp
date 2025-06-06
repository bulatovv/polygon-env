#include "testlib.h"
#include <bits/stdc++.h>
 
std::string upper(std::string sa)
{
    for (size_t i = 0; i < sa.length(); i++)
        if ('a' <= sa[i] && sa[i] <= 'z')
            sa[i] = sa[i] - 'a' + 'A';
    return sa;
}

bool comp_fraction(long long a1, long long b1, long long a2, long long b2) {
    long long g1 = std::gcd(a1, b1);
    a1 /= g1;
    b1 /= g1;
    
    long long g2 = std::gcd(a2, b2);
    a2 /= g2;
    b2 /= g2;
    
    return a1 == a2 && b1 == b2;
}
 
constexpr long long INF = 1'000'000;
 
int main(int argc, char * argv[])
{
    setName("YES or NO (with answer)");
    registerTestlibCmd(argc, argv);
    
    int n = inf.readInt();
    inf.readEoln();
    std::string s = inf.readString(); // there is no need to validate input file in the checker
    long long c = std::atoll(s.c_str());
    
    long long b = 1;
    while (n--) {
        b *= 10;
    }
 
    std::string ja = upper(ans.readWord("YES | NO", "ja"));
    std::string pa = upper(ouf.readWord("YES | NO", "pa"));
 
    if (pa != "YES" && pa != "NO")
        quitf(_pe, "YES or NO expected, but %s found", pa.c_str());
 
    if (ja != "YES" && ja != "NO")
        quitf(_fail, "YES or NO expected in answer, but %s found", ja.c_str());
 
    if (ja != pa) {
        if (pa == "YES") {
            long long ouf_a = ouf.readLong(1, INF - 1, "out_a");
            long long ouf_b = ouf.readLong(1, INF - 1, "out_b");
            pa += " " + std::to_string(ouf_a) + " " + std::to_string(ouf_b);
            ensuref(!comp_fraction(c, b, ouf_a, ouf_b), "Jury fail %s", ja.c_str());
        } else {
            long long ans_a = ans.readLong(1, INF - 1, "ans_a");
            long long ans_b = ans.readLong(1, INF - 1, "ans_b");
            ja += " " + std::to_string(ans_a) + " " + std::to_string(ans_b);
            ensuref(comp_fraction(c, b, ans_a, ans_b), "Jury fail %s", ja.c_str());
        }
        quitf(_wa, "expected %s, found %s", ja.c_str(), pa.c_str());
    }
        
    if (ja == "YES") {
        
        long long ans_a = ans.readLong(1, INF - 1, "ans_a");
        long long ans_b = ans.readLong(1, INF - 1, "ans_b");
        
        ja += " " + std::to_string(ans_a) + " " + std::to_string(ans_b);
        
        long long ouf_a = ouf.readLong(1, INF - 1, "out_a");
        long long ouf_b = ouf.readLong(1, INF - 1, "out_b");
        
        pa += " " + std::to_string(ouf_a) + " " + std::to_string(ouf_b);
        
        ensuref(ans_a < ans_b, "Jury fail %s", ja.c_str());
        ensuref(ans_a != 0, "Jury fail %s", ja.c_str());
        ensuref(comp_fraction(c, b, ans_a, ans_b), "Jury fail %s", ja.c_str());
        
        if (ouf_a >= ouf_b) {
            quitf(_wa, "A must be less then B");
        }
        
        if (ouf_a == 0) {
            quitf(_wa, "expected %s, found %s", ja.c_str(), pa.c_str());
        }
        
        if (!comp_fraction(c, b, ouf_a, ouf_b)) {
            quitf(_wa, "expected %s, found %s", ja.c_str(), pa.c_str());
        }
    }
    
    quitf(_ok, "answer is %s", ja.c_str());
    
}