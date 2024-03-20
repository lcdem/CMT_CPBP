package minicpbp.examples;

import minicpbp.cp.Factory;
import minicpbp.engine.core.Constraint;
import minicpbp.engine.core.IntVar;
import minicpbp.engine.core.Solver;
import minicpbp.util.exception.InconsistencyException;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.io.PrintStream;
import java.util.*;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import static minicpbp.cp.Factory.among;
import static minicpbp.cp.Factory.makeIntVar;

public class rhythmPatternCorrelation {
    public static int nbVar = 128;
    public static int nbVarPerBar = 16;
    public static int nbBar = nbVar / nbVarPerBar;
    public static int nbVal = 3;
    public static int onSetToken = 2;

    public static void main(String[] args) {
        String filename = args[0];
        int nbSample = Integer.parseInt(args[1]);
        int idx = Integer.parseInt(args[2]);
        double oracleWeight = Double.parseDouble(args[3]);
        //int[][] sectionsMustBeEqual = new int[10][10];
        //double patternLength = Double.parseDouble(args[5]);
        // double patternCorrelation = 0.15;
        double[][] sectionPositionsRhythm = {{0.0, 0.1875, 0.25, 0.4375}}; //readSections("rhythms");//{ { 0.125, 0.25 }, { 0.375, 0.5 } }; // début - fin
        double[][] sectionPositionsPitch = {{0.625, 0.75, 0.875, 1.0}, {0.5, 0.5625, 0.75, 0.8125}};//readSections("notes");
        double[][] sectionPositionsInterval = {{0.5, 0.625, 0.875, 1.0}, {0.5, 0.5625, 0.9375, 1.0}}; //readSections("intervals"); //{{ 0.625, 0.75 }, {0.875, 1}};




        try {
            System.out.println();
            Scanner scanner = new Scanner(new FileReader("minicpbp/examples/data/MusicCP/" + filename));
            redirectStdout(filename);

            for (int j = 0; j < nbSample; j++) {
                Solver cp = Factory.makeSolver();

                IntVar[] x = new IntVar[nbVar]; // taille: 128
                for (int i = 0; i < nbVar; i++) {
                    x[i] = makeIntVar(cp, 0, nbVal-1);
                    x[i].setName("x"+"["+i+"]");
                }
                initVar(x, nbVar, nbVal, idx, scanner);

                double[] marginal = new double[nbVal]; // tableau initialisé de taille 3
                int[] v = new int[nbVal]; // v prend trois valeurs: 0, 1, 2 (tokens)
                for (int i = 0; i < nbVal; i++) {
                    marginal[i] = (x[idx].contains(i) ? x[idx].marginal(i) : 0); // marginal de i sera soit sa marginale existante (?) soit 0
                    v[i] = i; // on remplit v => v[0] = 0, etc
                }


                for (int i = 0; i < sectionPositionsRhythm.length; i++) {
                    int start_sec1 = (int) Math.round(sectionPositionsRhythm[i][0] * nbVar);
                    int end_sec1 = (int) Math.round(sectionPositionsRhythm[i][1] * nbVar);
                    int start_sec2 = (int) Math.round(sectionPositionsRhythm[i][2] * nbVar);

                    
                    for (int k = start_sec1, m = start_sec2; k < end_sec1; k++, m++) {
                        cp.post(Factory.equal(x[k], x[m]));
                    
                    }
                }
                for (int i = 0; i < sectionPositionsPitch.length; i++) {
                    int start_sec1 = (int) Math.round(sectionPositionsPitch[i][0] * nbVar);
                    int end_sec1 = (int) Math.round(sectionPositionsPitch[i][1] * nbVar);
                    int start_sec2 = (int) Math.round(sectionPositionsPitch[i][2] * nbVar);
                    int end_sec2 = (int) Math.round(sectionPositionsPitch[i][3] * nbVar);
                    
                    IntVar[] subArray1 = Arrays.copyOfRange(x, start_sec1, end_sec1);
                    IntVar[] subArray2 = Arrays.copyOfRange(x, start_sec2, end_sec2);
                    IntVar o = makeIntVar(cp, 0, subArray1.length);
                    cp.post(among(subArray1, onSetToken, o));
                    cp.post(among(subArray2, onSetToken, o));
                    
                }
                for (int i = 0; i < sectionPositionsInterval.length; i++) {
                    
                    int start_sec1 = (int) Math.round(sectionPositionsInterval[i][0] * nbVar);
                    int end_sec1 = (int) Math.round(sectionPositionsInterval[i][1] * nbVar);
                    int start_sec2 = (int) Math.round(sectionPositionsInterval[i][2] * nbVar);
                    int end_sec2 = (int) Math.round(sectionPositionsInterval[i][3] * nbVar);
                    
                    IntVar[] subArray1 = Arrays.copyOfRange(x, start_sec1, end_sec1);
                    IntVar[] subArray2 = Arrays.copyOfRange(x, start_sec2, end_sec2);
                    IntVar o = makeIntVar(cp, 0, subArray1.length);
                    cp.post(among(subArray1, onSetToken, o));
                    cp.post(among(subArray2, onSetToken, o));
                    
                }




                Constraint orac = Factory.oracle(x[idx], v, marginal);
                orac.setWeight(oracleWeight);
                cp.post(orac);

                cp.fixPoint();
                cp.beliefPropa();

                for (int i = 0; i < nbVal; i++) {
                    System.out.print((x[idx].contains(i) ? x[idx].marginal(i) : 0) + " ");
                }
                System.out.println();
            }
            scanner.close();
        }
        catch (IOException e) {
            System.err.println("Error 1: " + e.getMessage()) ;
            System.exit(1) ;
        }
        catch (InconsistencyException e) {
            System.err.println("Error 2: " + "Inconsistency Exception");
            System.exit(2) ;
        }
        catch (Exception  e) {
            System.err.println("Error 3: " + e.getMessage());
            System.exit(3) ;
        }
    }

    public static void redirectStdout(String filename) {
        try {
            PrintStream fileOut = new PrintStream("minicpbp/examples/data/MusicCP/" + filename.substring(0, filename.length() - 4) + "_results.dat");
            System.setOut(fileOut);
        }
        catch(FileNotFoundException e) {
            System.err.println("Error 1: " + e.getMessage()) ;
            System.exit(1) ;
        }
    }

    public static void initVar(IntVar[] x, int nbVar, int nbVal, int idx, Scanner s){
        // set value of previously fixed vars
        for (int i = 0; i < idx; i++) {
            int token = s.nextInt();
            x[i].assign(token);
        }

        // set marginals for variable being fixed
        for (int i = 0; i < nbVal; i++) {
            double score = s.nextDouble();
            if (x[idx].contains(i)) {
                x[idx].setMarginal(i, score);
            }
        }
        x[idx].normalizeMarginals();

        // set  marginals for following variables
        for (int i = idx + 1; i < nbVar; i++) {
            double score = s.nextDouble();
            if (x[idx].contains(i)) {
                x[idx].setMarginal(i, score);
            }
        }
    }

    public static double[][] readSections(String type) {
        
        double[][] sections = {};

        ObjectMapper objectMapper = new ObjectMapper();
        try {
            // Assuming the JSON file is named "sections_your_title_here.json"
            File file = new File("minicpbp/examples/data/MusicCP/"+type+"_sections.json");
            
            // Use TypeReference to inform Jackson about the Map's structure
            Map<String, double[][]> result = objectMapper.readValue(file, new TypeReference<Map<String, double[][]>>() {});

            sections = result.get("sections");
            
        } catch (IOException e) {
            e.printStackTrace();
        }
            
        return sections;
    }

}
